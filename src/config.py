import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.reload_from_env()

    def reload_from_env(self):
        """Reload configuration from environment variables"""
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.OPENAI_TIER: int = int(os.getenv("OPENAI_TIER", "1"))
        self.OPENAI_MAX_TOKENS: int = int(
            os.getenv("OPENAI_MAX_TOKENS", "1000")
        )
        self.OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))

        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        self.FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
        self.TESSERACT_CMD: Optional[str] = os.getenv("TESSERACT_CMD")

        self.SCENE_THRESHOLD: float = float(
            os.getenv("SCENE_THRESHOLD", "0.3")
        )
        self.MAX_SLIDES: int = int(os.getenv("MAX_SLIDES", "100"))
        self.MIN_SLIDE_DURATION: float = float(
            os.getenv("MIN_SLIDE_DURATION", "2.0")
        )

        self.RETRY_MAX_ATTEMPTS: int = int(
            os.getenv("RETRY_MAX_ATTEMPTS", "3")
        )
        self.RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))

        self.OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "videos")
        self.TRANSCRIPTS_DIR: str = os.getenv("TRANSCRIPTS_DIR", "transcripts")
        self.SLIDES_DIR: str = os.getenv("SLIDES_DIR", "slides")

        self.DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")

    def get_rate_limits(self):
        """Get rate limits based on OpenAI tier"""
        # Rate limits per minute for different tiers
        tier_limits = {
            0: {"requests": 3, "tokens": 40000},  # Free tier
            1: {"requests": 500, "tokens": 30000},  # Tier 1 ($5+ spent)
            2: {"requests": 5000, "tokens": 450000},  # Tier 2 ($50+ spent)
            3: {"requests": 5000, "tokens": 2000000},  # Tier 3 ($100+ spent)
            4: {"requests": 10000, "tokens": 5000000},  # Tier 4 ($1000+ spent)
            5: {"requests": 10000, "tokens": 5000000},  # Tier 5 ($5000+ spent)
        }
        return tier_limits.get(self.OPENAI_TIER, tier_limits[1])

    def get_delay_between_requests(self):
        """Get recommended delay between requests"""
        limits = self.get_rate_limits()
        # Use 80% of rate limit for safety margin
        safe_requests_per_minute = limits["requests"] * 0.8
        return 60.0 / safe_requests_per_minute  # seconds between requests

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~4 characters per token"""
        return len(text) // 4 + 500  # Add buffer for response

    def validate(self) -> None:
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def get_video_dir(self, video_id: str) -> str:
        """Get the main directory for a video (contains all related files)"""
        video_dir = os.path.join(self.OUTPUT_DIR, video_id)
        os.makedirs(video_dir, exist_ok=True)
        return video_dir

    def get_slides_dir(self, video_id: str) -> str:
        """Get the slides directory for a video"""
        slides_dir = os.path.join(self.get_video_dir(video_id), "slides")
        os.makedirs(slides_dir, exist_ok=True)
        return slides_dir

    def get_transcript_path(self, video_id: str) -> str:
        """Get the transcript file path for a video"""
        video_dir = self.get_video_dir(video_id)
        return os.path.join(video_dir, "transcript.json")

    def get_output_path(self, video_id: str, format_type: str = "md") -> str:
        """Get the output file path for a video"""
        video_dir = self.get_video_dir(video_id)
        return os.path.join(video_dir, f"summary.{format_type}")

    @staticmethod
    def get_video_id_from_url(url: str) -> str:
        import re

        # If it's already just a video ID (11 characters, alphanumeric + - and _)
        if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
            return url

        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)",
            r"youtube\.com/watch\?.*v=([^&\n?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract video ID from URL: {url}")
