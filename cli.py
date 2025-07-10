#!/usr/bin/env python3

import argparse
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config import Config
from src.downloader import TranscriptDownloader
from src.slides import SlideExtractor
from src.aligner import TranscriptSlideAligner
from src.ocr import SlideOCR
from src.summarizer import SlideSummarizer
from src.output import OutputGenerator
from src.utils.logger import setup_logger


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Extract and summarize slides from YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py https://www.youtube.com/watch?v=VIDEO_ID
  python cli.py VIDEO_ID --output-format json --scene-threshold 0.2
  python cli.py https://youtu.be/VIDEO_ID --dry-run --no-ocr
  python cli.py VIDEO_ID --language es --max-slides 20
        """,
    )

    parser.add_argument("url_or_id", help="YouTube URL or video ID")

    parser.add_argument(
        "--output-format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    parser.add_argument(
        "--scene-threshold",
        type=float,
        help="Scene change detection threshold (0.1-1.0, default: 0.3)",
    )

    parser.add_argument(
        "--language",
        default="en",
        help="Transcript language code (default: en)",
    )

    parser.add_argument(
        "--max-slides", type=int, help="Maximum number of slides to extract"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process slides but don't call OpenAI API",
    )

    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Skip OCR text extraction from slides",
    )

    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Use text-only summarization instead of vision model",
    )

    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary files (video, extracted slides)",
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    parser.add_argument("--output-dir", help="Output directory for reports")

    return parser.parse_args()


def validate_args(args, config):
    if args.scene_threshold is not None:
        if not 0.1 <= args.scene_threshold <= 1.0:
            raise ValueError("Scene threshold must be between 0.1 and 1.0")
        config.SCENE_THRESHOLD = args.scene_threshold

    if args.max_slides is not None:
        if args.max_slides < 1:
            raise ValueError("Max slides must be at least 1")
        config.MAX_SLIDES = args.max_slides

    if args.log_level:
        config.LOG_LEVEL = args.log_level

    if args.output_dir:
        config.OUTPUT_DIR = args.output_dir


def main():
    try:
        args = parse_arguments()

        # Initialize configuration
        config = Config()
        validate_args(args, config)

        # Set up logging (both console and file)
        log_file = "debug.log"
        logger = setup_logger(
            "youtube-slide-summarizer", config.LOG_LEVEL, log_file
        )

        logger.info("Starting YouTube Slide Summarizer")

        # Validate configuration
        if not args.dry_run:
            config.validate()

        # Extract video ID
        try:
            logger.debug(f"Input URL/ID: {args.url_or_id}")
            video_id = config.get_video_id_from_url(args.url_or_id)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Processing video: {video_id}")
            logger.debug(f"Video URL: {video_url}")
        except ValueError as e:
            logger.error(f"Invalid URL or video ID: {e}")
            logger.debug(f"Failed to parse: '{args.url_or_id}'")
            return 1

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
            transcript = downloader.download_transcript(
                video_id, args.language
            )
            transcript_path = downloader.save_transcript(transcript, video_id)
            logger.info(f"Transcript saved: {transcript_path}")
        except Exception as e:
            logger.error(f"Failed to download transcript: {e}")
            return 1

        # Step 2: Extract slides
        logger.info("Step 2: Extracting slides...")
        try:
            slides = slide_extractor.extract_slides(
                video_id, config.SCENE_THRESHOLD
            )
            if not slides:
                logger.error("No slides were extracted from the video")
                return 1
            logger.info(f"Extracted {len(slides)} slides")
        except Exception as e:
            logger.error(f"Failed to extract slides: {e}")
            return 1

        # Step 3: Align transcript with slides
        logger.info("Step 3: Aligning transcript with slides...")
        try:
            aligned_slides = aligner.align_transcript_with_slides(
                transcript, slides
            )

            # Filter slides with minimal content
            aligned_slides = aligner.filter_slides_by_content(
                aligned_slides, min_words=3
            )

            if not aligned_slides:
                logger.error("No slides with sufficient content found")
                return 1

            # Print alignment stats
            stats = aligner.get_alignment_stats(aligned_slides)
            logger.info(
                f"Alignment stats: {stats['total_slides']} slides, "
                f"{stats['total_words']} words, "
                f"{stats['avg_words_per_slide']:.1f} avg words per slide"
            )
        except Exception as e:
            logger.error(f"Failed to align transcript with slides: {e}")
            return 1

        # Step 4: OCR (optional)
        if ocr and not args.no_ocr:
            logger.info("Step 4: Extracting text from slides...")
            try:
                aligned_slides = ocr.extract_text_from_slides(aligned_slides)
                aligned_slides = ocr.combine_transcript_and_ocr(aligned_slides)
                logger.info("OCR processing completed")
            except Exception as e:
                logger.warning(f"OCR processing failed: {e}")
        else:
            logger.info("Step 4: Skipping OCR processing")

        # Step 5: Summarize slides
        if args.dry_run:
            logger.info("Step 5: Running in dry-run mode...")
            summarizer_temp = SlideSummarizer(config)
            summarized_slides = summarizer_temp.dry_run(aligned_slides)
            batch_summary = summarizer_temp.create_batch_summary(
                summarized_slides
            )
        else:
            logger.info("Step 5: Generating summaries...")
            try:
                use_vision = not args.no_vision
                summarized_slides = summarizer.summarize_slides(
                    aligned_slides, use_vision
                )
                batch_summary = summarizer.create_batch_summary(
                    summarized_slides
                )
                logger.info(
                    f"Generated summaries for {len(summarized_slides)} slides"
                )
            except Exception as e:
                logger.error(f"Failed to generate summaries: {e}")
                return 1

        # Step 6: Generate output
        logger.info("Step 6: Generating output...")
        try:
            output_path = output_generator.generate_output(
                summarized_slides,
                video_id,
                args.output_format,
                video_url,
                batch_summary,
            )

            output_summary = output_generator.get_output_summary(output_path)
            logger.info(f"Output generated: {output_path}")
            logger.info(
                f"File size: {output_summary.get('file_size_mb', 0):.2f} MB"
            )

        except Exception as e:
            logger.error(f"Failed to generate output: {e}")
            return 1

        # Cleanup
        if not args.keep_temp:
            logger.info("Cleaning up temporary files...")
            output_generator.cleanup_temp_files(video_id, keep_slides=True)

        # Success summary
        print("\n" + "=" * 50)
        print("✅ Processing completed successfully!")
        print(f"📁 Output file: {output_path}")
        print(f"📊 Slides processed: {len(summarized_slides)}")
        if batch_summary:
            main_topics = batch_summary.get("main_topics", [])
            if main_topics:
                print(f"🏷️  Main topics: {', '.join(main_topics[:3])}")
        print("=" * 50)

        return 0

    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if "--log-level" in sys.argv or "DEBUG" in os.environ.get(
            "LOG_LEVEL", ""
        ):
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
