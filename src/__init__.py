"""
video-extract: AI-powered YouTube video transcript and slide analyzer

A Python CLI tool that processes YouTube videos to extract transcripts, detect slide changes,
align content, and generate AI-powered summaries using OpenAI's API.
"""

__version__ = "1.0.0"
__author__ = "Philipp"
__license__ = "MIT"

from .config import Config
from .downloader import TranscriptDownloader
from .slides import SlideExtractor
from .aligner import TranscriptSlideAligner
from .ocr import SlideOCR
from .summarizer import SlideSummarizer
from .output import OutputGenerator

__all__ = [
    "Config",
    "TranscriptDownloader",
    "SlideExtractor",
    "TranscriptSlideAligner",
    "SlideOCR",
    "SlideSummarizer",
    "OutputGenerator",
]
