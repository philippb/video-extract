import os
import json
import yt_dlp
from typing import List, Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
)
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TranscriptDownloader:
    def __init__(self, config: Config):
        self.config = config

    def download_transcript(
        self, video_id: str, language: str = None
    ) -> List[Dict[str, Any]]:
        language = language or self.config.DEFAULT_LANGUAGE

        transcript = self._try_official_transcript(video_id, language)
        if transcript:
            logger.info(f"Downloaded official transcript for {video_id}")
            return transcript

        transcript = self._try_ytdlp_transcript(video_id, language)
        if transcript:
            logger.info(f"Downloaded auto-generated transcript for {video_id}")
            return transcript

        raise RuntimeError(
            f"Could not retrieve transcript for video {video_id}"
        )

    def _try_official_transcript(
        self, video_id: str, language: str
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            try:
                transcript = transcript_list.find_transcript([language])
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(
                    [language]
                )

            raw_transcript = transcript.fetch()
            logger.debug(
                f"Raw transcript type: {type(raw_transcript)}, length: {len(raw_transcript)}"
            )
            return self._normalize_transcript(raw_transcript)

        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.debug(f"Official transcript not available: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error fetching official transcript: {e}")
            return None

    def _try_ytdlp_transcript(
        self, video_id: str, language: str
    ) -> Optional[List[Dict[str, Any]]]:
        try:
            ydl_opts = {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": [language],
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
            }

            url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                subtitles = info.get("subtitles", {})
                auto_captions = info.get("automatic_captions", {})

                available_subs = subtitles.get(language) or auto_captions.get(
                    language
                )

                if not available_subs:
                    logger.debug(f"No subtitles found for language {language}")
                    return None

                vtt_url = None
                for sub in available_subs:
                    if sub.get("ext") == "vtt":
                        vtt_url = sub.get("url")
                        break

                if not vtt_url:
                    logger.debug("No VTT subtitle format found")
                    return None

                return self._download_and_parse_vtt(vtt_url)

        except Exception as e:
            logger.warning(f"Error with yt-dlp transcript: {e}")
            return None

    def _download_and_parse_vtt(self, vtt_url: str) -> List[Dict[str, Any]]:
        import requests

        try:
            response = requests.get(vtt_url, timeout=30)
            response.raise_for_status()

            vtt_content = response.text
            return self._parse_vtt_content(vtt_content)

        except Exception as e:
            logger.error(f"Error downloading VTT: {e}")
            return []

    def _parse_vtt_content(self, vtt_content: str) -> List[Dict[str, Any]]:
        import re

        transcript = []
        lines = vtt_content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if "-->" in line:
                time_match = re.match(
                    r"^(\d{2}):(\d{2}):(\d{2}\.\d{3}) --> (\d{2}):(\d{2}):(\d{2}\.\d{3})",
                    line,
                )
                if time_match:
                    start_time = self._time_to_seconds(time_match.groups()[:3])
                    end_time = self._time_to_seconds(time_match.groups()[3:])

                    i += 1
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1

                    if text_lines:
                        text = " ".join(text_lines)
                        text = re.sub(r"<[^>]+>", "", text)
                        text = text.strip()

                        if text:
                            transcript.append(
                                {
                                    "start": start_time,
                                    "end": end_time,
                                    "text": text,
                                }
                            )
            i += 1

        return transcript

    def _time_to_seconds(self, time_parts: tuple) -> float:
        hours, minutes, seconds = time_parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    def _normalize_transcript(
        self, raw_transcript: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        normalized = []
        for entry in raw_transcript:
            # Handle both dict and object types
            if hasattr(entry, "__dict__"):
                # Convert object to dict
                entry_dict = {
                    "start": getattr(entry, "start", 0.0),
                    "duration": getattr(entry, "duration", 0.0),
                    "text": getattr(entry, "text", "").strip(),
                }
            else:
                entry_dict = entry

            normalized.append(
                {
                    "start": entry_dict.get("start", 0.0),
                    "end": entry_dict.get("start", 0.0)
                    + entry_dict.get("duration", 0.0),
                    "text": entry_dict.get("text", "").strip(),
                }
            )
        return normalized

    def save_transcript(
        self, transcript: List[Dict[str, Any]], video_id: str
    ) -> str:
        output_path = self.config.get_transcript_path(video_id)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved transcript to {output_path}")
        return output_path

    def load_transcript(self, video_id: str) -> Optional[List[Dict[str, Any]]]:
        transcript_path = self.config.get_transcript_path(video_id)

        if not os.path.exists(transcript_path):
            return None

        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading transcript: {e}")
            return None
