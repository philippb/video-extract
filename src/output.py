import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OutputGenerator:
    def __init__(self, config: Config):
        self.config = config

    def generate_output(
        self,
        summarized_slides: List[Dict[str, Any]],
        video_id: str,
        format_type: str = "markdown",
        video_url: Optional[str] = None,
        batch_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        if format_type.lower() == "json":
            return self._generate_json_output(
                summarized_slides, video_id, video_url, batch_summary
            )
        else:
            return self._generate_markdown_output(
                summarized_slides, video_id, video_url, batch_summary
            )

    def _generate_markdown_output(
        self,
        summarized_slides: List[Dict[str, Any]],
        video_id: str,
        video_url: Optional[str] = None,
        batch_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        output_path = self.config.get_output_path(video_id, "md")

        content = self._create_markdown_content(
            summarized_slides, video_id, video_url, batch_summary
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated markdown report: {output_path}")
        return output_path

    def _generate_json_output(
        self,
        summarized_slides: List[Dict[str, Any]],
        video_id: str,
        video_url: Optional[str] = None,
        batch_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        output_path = self.config.get_output_path(video_id, "json")

        output_data = {
            "video_id": video_id,
            "video_url": video_url,
            "generated_at": datetime.now().isoformat(),
            "batch_summary": batch_summary,
            "slides": summarized_slides,
            "metadata": {
                "total_slides": len(summarized_slides),
                "tool_version": "1.0.0",
                "config": {
                    "scene_threshold": self.config.SCENE_THRESHOLD,
                    "max_slides": self.config.MAX_SLIDES,
                    "min_slide_duration": self.config.MIN_SLIDE_DURATION,
                },
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Generated JSON report: {output_path}")
        return output_path

    def _create_markdown_content(
        self,
        summarized_slides: List[Dict[str, Any]],
        video_id: str,
        video_url: Optional[str] = None,
        batch_summary: Optional[Dict[str, Any]] = None,
    ) -> str:
        lines = []

        lines.append(f"# Video Analysis Report: {video_id}")
        lines.append("")
        lines.append(
            "*Complete analysis including slide screenshots, OCR text extraction, "
            "spoken content transcription, and AI-powered summaries.*"
        )
        lines.append("")

        if video_url:
            lines.append(f"**Video URL:** {video_url}")
            lines.append("")

        lines.append(
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"**Total Slides:** {len(summarized_slides)}")
        lines.append("")

        lines.append("## Content Overview")
        lines.append("")
        lines.append("Each slide includes:")
        lines.append("- 📸 **Screenshot** of the slide")
        lines.append("- 📄 **OCR Text** - All text visible on the slide")
        lines.append("- 🎤 **Transcript** - What was spoken during this slide")
        lines.append("- 🤖 **AI Summary** - Key insights and analysis")
        lines.append("")

        if batch_summary:
            lines.append("## Overview")
            lines.append("")
            lines.append(
                f"- **Total slides processed:** {batch_summary.get('total_slides', 0)}"
            )
            lines.append(
                f"- **Slides with content:** {batch_summary.get('slides_with_content', 0)}"
            )

            main_topics = batch_summary.get("main_topics", [])
            if main_topics:
                lines.append(
                    f"- **Main topics:** {', '.join(main_topics[:5])}"
                )
            lines.append("")

        lines.append("## Table of Contents")
        lines.append("")

        for slide in summarized_slides:
            slide_num = slide.get("slide_number", "Unknown")
            title = slide.get("title", f"Slide {slide_num}")
            timestamp = slide.get("timestamp", 0)

            lines.append(
                f"- [Slide {slide_num}: {title}](#slide-{slide_num}) "
                f"({self._format_timestamp(timestamp)})"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

        for slide in summarized_slides:
            slide_content = self._create_slide_markdown(slide)
            lines.append(slide_content)
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append(
            "*Generated by video-extract - AI-powered video analysis tool*"
        )
        lines.append("")
        lines.append("**Legend:**")
        lines.append(
            "- 📄 OCR text shows exactly what text appears on each slide"
        )
        lines.append(
            "- 🎤 Transcript shows what was spoken during each slide segment"
        )
        lines.append("- 🤖 AI summaries provide analysis and key insights")
        lines.append("- ⚠️ Low confidence OCR may contain transcription errors")

        return "\n".join(lines)

    def _create_slide_markdown(self, slide: Dict[str, Any]) -> str:
        lines = []

        slide_num = slide.get("slide_number", "Unknown")
        title = slide.get("title", f"Slide {slide_num}")
        timestamp = slide.get("timestamp", 0)

        lines.append(f"## Slide {slide_num}: {title}")
        lines.append("")
        lines.append(f"**Timestamp:** {self._format_timestamp(timestamp)}")

        duration = slide.get("duration", 0)
        if duration > 0:
            lines.append(f"**Duration:** {duration:.1f}s")

        word_count = slide.get("word_count", 0)
        if word_count > 0:
            lines.append(f"**Word count:** {word_count}")

        lines.append("")

        image_path = slide.get("image_path")
        if image_path and os.path.exists(image_path):
            # Get relative path from the summary file to the image
            video_dir = self.config.get_video_dir(slide.get("video_id", ""))
            relative_path = os.path.relpath(image_path, video_dir)
            lines.append(f"![Slide {slide_num}]({relative_path})")
            lines.append("")

        # Show OCR text prominently right after the image
        ocr_text = slide.get("ocr_text", "")
        ocr_confidence = slide.get("ocr_confidence", 0)
        if ocr_text:
            lines.append("### 📄 Text Visible on Slide")
            lines.append("")
            lines.append("```")
            lines.append(ocr_text.strip())
            lines.append("```")
            lines.append("")
            if ocr_confidence > 0:
                confidence_note = f"*OCR Confidence: {ocr_confidence:.2f}*"
                if ocr_confidence < 0.5:
                    confidence_note += (
                        " ⚠️ *Low confidence - text may be inaccurate*"
                    )
                lines.append(confidence_note)
                lines.append("")

        # Show transcript content
        transcript_text = slide.get("transcript_text", "")
        if transcript_text:
            lines.append("### 🎤 Spoken Content (Transcript)")
            lines.append("")
            lines.append("```")
            lines.append(transcript_text.strip())
            lines.append("```")
            lines.append("")

        # AI-generated summary and analysis
        summary = slide.get("summary", "")
        if summary:
            lines.append("### 🤖 AI Summary")
            lines.append("")
            lines.append(summary)
            lines.append("")

        key_points = slide.get("key_points", [])
        if key_points:
            lines.append("### 🔑 Key Points")
            lines.append("")
            for point in key_points:
                lines.append(f"- {point}")
            lines.append("")

        topics = slide.get("topics", [])
        if topics:
            lines.append("### 🏷️ Topics")
            lines.append("")
            lines.append(f"**Tags:** {', '.join(topics)}")
            lines.append("")

        lines.append("---")

        return "\n".join(lines)

    def _format_timestamp(self, timestamp: float) -> str:
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def create_index_file(self, processed_videos: List[str]) -> str:
        index_path = os.path.join(self.config.OUTPUT_DIR, "index.md")

        lines = []
        lines.append("# YouTube Slide Summaries Index")
        lines.append("")
        lines.append(
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        lines.append(f"**Total videos processed:** {len(processed_videos)}")
        lines.append("")

        lines.append("## Processed Videos")
        lines.append("")

        for video_id in processed_videos:
            markdown_file = f"{video_id}.md"
            json_file = f"{video_id}.json"

            lines.append(f"### {video_id}")

            if os.path.exists(
                os.path.join(self.config.OUTPUT_DIR, markdown_file)
            ):
                lines.append(f"- [Markdown Report]({markdown_file})")

            if os.path.exists(os.path.join(self.config.OUTPUT_DIR, json_file)):
                lines.append(f"- [JSON Data]({json_file})")

            slides_dir = os.path.join(self.config.SLIDES_DIR, video_id)
            if os.path.exists(slides_dir):
                slide_count = len(
                    [f for f in os.listdir(slides_dir) if f.endswith(".png")]
                )
                lines.append(f"- Slides extracted: {slide_count}")

            lines.append("")

        content = "\n".join(lines)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated index file: {index_path}")
        return index_path

    def cleanup_temp_files(
        self, video_id: str, keep_slides: bool = True
    ) -> None:
        if not keep_slides:
            slides_dir = self.config.get_slides_dir(video_id)
            if os.path.exists(slides_dir):
                import shutil

                shutil.rmtree(slides_dir)
                logger.info(f"Cleaned up slides directory: {slides_dir}")

        video_dir = self.config.get_video_dir(video_id)
        logger.debug(f"Keeping video directory: {video_dir}")

    def get_output_summary(self, output_path: str) -> Dict[str, Any]:
        if not os.path.exists(output_path):
            return {}

        file_size = os.path.getsize(output_path)
        file_ext = os.path.splitext(output_path)[1].lower()

        summary = {
            "file_path": output_path,
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "format": file_ext.replace(".", ""),
            "created_at": datetime.fromtimestamp(
                os.path.getctime(output_path)
            ).isoformat(),
        }

        if file_ext == ".json":
            try:
                with open(output_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    summary["slides_count"] = len(data.get("slides", []))
                    summary["has_batch_summary"] = bool(
                        data.get("batch_summary")
                    )
            except Exception:
                pass

        return summary
