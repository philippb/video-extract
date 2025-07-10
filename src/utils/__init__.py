"""
Utility modules for video-extract
"""

from .logger import get_logger
from .ffmpeg_wrapper import FFmpegWrapper

__all__ = [
    "get_logger",
    "FFmpegWrapper",
]
