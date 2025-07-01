#!/usr/bin/env python3

import argparse
import sys
import os
import shutil
import subprocess
from typing import Optional
from pathlib import Path

try:
    # Package imports (when installed)
    from .config import Config
    from .downloader import TranscriptDownloader
    from .slides import SlideExtractor
    from .aligner import TranscriptSlideAligner
    from .ocr import SlideOCR
    from .summarizer import SlideSummarizer
    from .output import OutputGenerator
    from .utils.logger import setup_logger
except ImportError:
    # Direct imports (when running from source)
    sys.path.insert(0, os.path.dirname(__file__))
    from config import Config
    from downloader import TranscriptDownloader
    from slides import SlideExtractor
    from aligner import TranscriptSlideAligner
    from ocr import SlideOCR
    from summarizer import SlideSummarizer
    from output import OutputGenerator
    from utils.logger import setup_logger


def get_config_dir():
    """Get the configuration directory for video-extract"""
    return Path.home() / ".video-extract"


def get_env_example_path():
    """Get path to .env.example file"""
    # Look for .env.example in package directory or parent directory
    possible_paths = [
        Path(__file__).parent.parent / ".env.example",  # Parent of src/
        Path(__file__).parent / ".env.example",  # In src/
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # If not found, return the expected location
    return Path(__file__).parent.parent / ".env.example"


def init_command():
    """Initialize video-extract configuration with API key prompt"""
    print("🚀 Initializing video-extract...")
    
    # Create config directory
    config_dir = get_config_dir()
    config_dir.mkdir(exist_ok=True)
    print(f"📁 Config directory: {config_dir}")
    
    env_path = config_dir / ".env"
    
    if env_path.exists():
        print(f"⚠️  Configuration already exists at {env_path}")
        response = input("Reinitialize? (y/N): ").strip().lower()
        if response != 'y':
            print("✅ Keeping existing configuration")
            print(f"💡 Use 'video-extract config' to edit settings")
            return
    
    # Prompt for OpenAI API key
    print("\n🔑 OpenAI API Key Setup")
    print("Get your API key from: https://platform.openai.com/api-keys")
    
    api_key = input("\nEnter your OpenAI API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided. Initialization cancelled.")
        return
    
    # Ask for optional tier
    print("\n📊 OpenAI Usage Tier (for rate limiting optimization)")
    print("0 = Free tier, 1 = Tier 1 ($5+ spent), 2+ = Higher tiers")
    tier_input = input("Enter your tier (default: 1): ").strip()
    tier = tier_input if tier_input.isdigit() and 0 <= int(tier_input) <= 5 else "1"
    
    # Create configuration file
    config_content = f"""# OpenAI Configuration (Required)
OPENAI_API_KEY={api_key}
OPENAI_MODEL=gpt-4o
OPENAI_MAX_TOKENS=1000
OPENAI_TIMEOUT=30
OPENAI_TIER={tier}

# Logging Configuration
LOG_LEVEL=INFO

# Tool Paths
FFMPEG_PATH=ffmpeg
TESSERACT_CMD=tesseract

# Video Processing Settings
SCENE_THRESHOLD=0.3
MAX_SLIDES=100
MIN_SLIDE_DURATION=2.0

# Directory Configuration
OUTPUT_DIR=videos
TRANSCRIPTS_DIR=transcripts
SLIDES_DIR=slides

# Language Settings
DEFAULT_LANGUAGE=en
"""
    
    with open(env_path, 'w') as f:
        f.write(config_content)
    
    print(f"\n✅ Configuration saved to: {env_path}")
    print(f"🎉 video-extract is ready to use!")
    print(f"\nNext steps:")
    print(f"• Process a video: video-extract <VIDEO_ID>")
    print(f"• Edit settings: video-extract config")
    print(f"• Get help: video-extract --help")


def config_command():
    """Open configuration file in editor"""
    config_dir = get_config_dir()
    env_path = config_dir / ".env"
    
    if not env_path.exists():
        print(f"❌ No configuration found at {env_path}")
        print("Run 'video-extract init' first to create configuration")
        return
    
    print(f"🔧 Opening configuration file: {env_path}")
    
    editor = os.environ.get('EDITOR', 'nano')
    try:
        subprocess.run([editor, str(env_path)], check=True)
        print("✅ Configuration updated")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌ Could not open editor '{editor}'")
        print(f"Please manually edit: {env_path}")
    except KeyboardInterrupt:
        print("\n✅ Editor closed")


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="video-extract",
        description="AI-powered YouTube video transcript and slide analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  video-extract init                                    # Setup with API key prompt
  video-extract config                                  # Edit configuration file
  video-extract "https://www.youtube.com/watch?v=VIDEO_ID"
  video-extract VIDEO_ID --output-format json --scene-threshold 0.2
  video-extract "https://youtu.be/VIDEO_ID" --dry-run --no-ocr
  video-extract VIDEO_ID --language es --max-slides 20
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize configuration with API key setup')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Open configuration file in editor')
    
    # For backward compatibility and when no subcommand is provided
    parser.add_argument(
        "url_or_id",
        nargs='?',
        help="YouTube URL or video ID"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "--scene-threshold",
        type=float,
        help="Scene change detection threshold (0.1-1.0, default: 0.3)"
    )
    
    parser.add_argument(
        "--language",
        default="en",
        help="Transcript language code (default: en)"
    )
    
    parser.add_argument(
        "--max-slides",
        type=int,
        help="Maximum number of slides to extract (default: 100)"
    )
    
    parser.add_argument(
        "--openai-tier",
        type=int,
        choices=[0, 1, 2, 3, 4, 5],
        help="OpenAI API tier for rate limiting (0-5, default: from config)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API calls for testing"
    )
    
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Skip OCR text extraction"
    )
    
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Use text-only AI summarization"
    )
    
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary files after processing"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for reports"
    )
    
    return parser.parse_args()


def validate_args(args, config):
    if args.scene_threshold is not None:
        if not 0.1 <= args.scene_threshold <= 1.0:
            raise ValueError("Scene threshold must be between 0.1 and 1.0")
        config.SCENE_THRESHOLD = args.scene_threshold
    
    if args.language:
        config.DEFAULT_LANGUAGE = args.language
    
    if args.openai_tier is not None:
        config.OPENAI_TIER = args.openai_tier
    
    if args.max_slides is not None:
        if args.max_slides < 1:
            raise ValueError("Max slides must be at least 1")
        config.MAX_SLIDES = args.max_slides
    
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    if args.output_dir:
        config.OUTPUT_DIR = args.output_dir


def load_config_from_user_dir():
    """Load configuration from user's config directory"""
    config_dir = get_config_dir()
    env_path = config_dir / ".env"
    
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        print(f"📋 Loaded configuration from: {env_path}")
    else:
        print(f"⚠️  No configuration found at {env_path}")
        print("Run 'video-extract init' to create configuration")


def main():
    try:
        args = parse_arguments()
        
        # Handle init command
        if args.command == 'init':
            init_command()
            return
        
        # Handle config command
        if args.command == 'config':
            config_command()
            return
        
        # Check if URL/ID is provided for extract command
        if not args.url_or_id:
            print("❌ Error: YouTube URL or video ID is required")
            print("Run 'video-extract --help' for usage information")
            print("Run 'video-extract init' to initialize configuration")
            sys.exit(1)
        
        # Load user configuration
        load_config_from_user_dir()
        
        # Initialize configuration
        config = Config()
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            print("Run 'video-extract init' to set up configuration")
            sys.exit(1)
        
        # Override config with command line arguments
        validate_args(args, config)
        
        # Setup logging
        logger = setup_logger(config.LOG_LEVEL)
        logger.info("Starting video-extract processing")
        
        # Extract video ID from URL if needed
        video_id = config.get_video_id_from_url(args.url_or_id)
        if not video_id:
            logger.error(f"Could not extract video ID from: {args.url_or_id}")
            sys.exit(1)
        
        logger.info(f"Processing video: {video_id}")
        logger.info(f"Output format: {args.output_format}")
        logger.info(f"Scene threshold: {config.SCENE_THRESHOLD}")
        logger.info(f"Max slides: {config.MAX_SLIDES}")
        
        # Initialize components
        downloader = TranscriptDownloader(config)
        slide_extractor = SlideExtractor(config)
        aligner = TranscriptSlideAligner()
        ocr = SlideOCR(config) if not args.no_ocr else None
        summarizer = SlideSummarizer(config) if not args.dry_run else None
        output_generator = OutputGenerator(config)
        
        # Step 1: Download transcript
        logger.info("Step 1: Downloading transcript...")
        try:
            transcript = downloader.download_transcript(video_id, args.language)
            transcript_path = downloader.save_transcript(transcript, video_id)
            logger.info(f"Transcript saved: {transcript_path}")
        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            sys.exit(1)
        
        # Step 2: Extract slides
        logger.info("Step 2: Extracting slides...")
        try:
            slides = slide_extractor.extract_slides(video_id)
            logger.info(f"Extracted {len(slides)} slides")
        except Exception as e:
            logger.error(f"Failed to extract slides: {e}")
            sys.exit(1)
        
        # Step 3: Align transcript with slides
        logger.info("Step 3: Aligning transcript with slides...")
        try:
            aligned_slides = aligner.align_transcript_with_slides(transcript, slides)
            logger.info(f"Aligned {len(aligned_slides)} slides with transcript")
        except Exception as e:
            logger.error(f"Failed to align transcript with slides: {e}")
            sys.exit(1)
        
        # Step 4: OCR (optional)
        if ocr and not args.no_ocr:
            logger.info("Step 4: Extracting text from slides...")
            try:
                aligned_slides = ocr.extract_text_from_slides(aligned_slides)
                logger.info("OCR processing completed")
            except Exception as e:
                logger.warning(f"OCR processing failed: {e}")
        
        # Step 5: Summarize slides
        if summarizer and not args.dry_run:
            logger.info("Step 5: Generating AI summaries...")
            try:
                use_vision = not args.no_vision
                summarized_slides = summarizer.summarize_slides(aligned_slides, use_vision=use_vision)
                logger.info(f"Generated summaries for {len(summarized_slides)} slides")
            except Exception as e:
                logger.error(f"Failed to generate summaries: {e}")
                sys.exit(1)
        else:
            logger.info("Step 5: Skipping AI summarization (dry run)")
            summarized_slides = aligned_slides
        
        # Step 6: Generate output
        logger.info("Step 6: Generating output...")
        try:
            if args.output_format == "json":
                output_path = output_generator.generate_json_report(video_id, summarized_slides)
            else:
                output_path = output_generator.generate_markdown_report(video_id, summarized_slides)
            
            logger.info(f"Output saved: {output_path}")
            print(f"\n✅ Processing complete!")
            print(f"📄 Report saved to: {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate output: {e}")
            sys.exit(1)
        
        # Cleanup temporary files if not keeping them
        if not args.keep_temp:
            logger.debug("Cleaning up temporary files...")
        
        logger.info("Processing completed successfully")
        
    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()