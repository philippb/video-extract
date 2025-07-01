import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-vision-preview")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    TESSERACT_CMD: Optional[str] = os.getenv("TESSERACT_CMD")
    
    SCENE_THRESHOLD: float = float(os.getenv("SCENE_THRESHOLD", "0.3"))
    MAX_SLIDES: int = int(os.getenv("MAX_SLIDES", "100"))
    MIN_SLIDE_DURATION: float = float(os.getenv("MIN_SLIDE_DURATION", "2.0"))
    
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "1.0"))
    
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "videos")
    TRANSCRIPTS_DIR: str = os.getenv("TRANSCRIPTS_DIR", "transcripts")
    SLIDES_DIR: str = os.getenv("SLIDES_DIR", "slides")
    
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")
    
    @classmethod
    def validate(cls) -> None:
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
    
    @classmethod
    def get_video_dir(cls, video_id: str) -> str:
        """Get the main directory for a video (contains all related files)"""
        video_dir = os.path.join(cls.OUTPUT_DIR, video_id)
        os.makedirs(video_dir, exist_ok=True)
        return video_dir
    
    @classmethod
    def get_slides_dir(cls, video_id: str) -> str:
        """Get the slides directory for a video"""
        slides_dir = os.path.join(cls.get_video_dir(video_id), "slides")
        os.makedirs(slides_dir, exist_ok=True)
        return slides_dir
    
    @classmethod
    def get_transcript_path(cls, video_id: str) -> str:
        """Get the transcript file path for a video"""
        video_dir = cls.get_video_dir(video_id)
        return os.path.join(video_dir, "transcript.json")
    
    @classmethod
    def get_output_path(cls, video_id: str, format_type: str = "md") -> str:
        """Get the output file path for a video"""
        video_dir = cls.get_video_dir(video_id)
        return os.path.join(video_dir, f"summary.{format_type}")
    
    @classmethod
    def get_video_id_from_url(cls, url: str) -> str:
        import re
        
        # If it's already just a video ID (11 characters, alphanumeric + - and _)
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")