# video-extract

AI-powered YouTube video transcript and slide analyzer. A powerful Python CLI tool that extracts YouTube video transcripts, detects slide changes, and generates AI-powered summaries of each slide using OpenAI's GPT models.

## Features

- 📺 **YouTube Integration**: Extracts transcripts from any public YouTube video
- 🎬 **Smart Slide Detection**: Uses FFmpeg scene detection to identify slide changes
- 🤖 **AI-Powered Summaries**: Leverages OpenAI GPT-4 Vision for intelligent slide analysis
- 🔍 **OCR Support**: Optional text extraction from slide images using Tesseract
- 📄 **Multiple Output Formats**: Generate reports in Markdown or JSON
- 🌍 **Multi-language Support**: Works with transcripts in various languages
- ⚙️ **Highly Configurable**: Extensive customization options
- 🔄 **Robust Error Handling**: Comprehensive retry logic and fallback mechanisms

## Installation

### Via Homebrew (Recommended)

For easy installation with all dependencies, use our Homebrew tap:

```bash
# Add the custom tap
brew tap philippb/video-extract

# Install video-extract with all dependencies
brew install video-extract

# Initialize configuration
video-extract init
```

For more details, see: https://github.com/philippb/homebrew-video-extract

### Manual Installation

#### Requirements

- Python 3.8+
- FFmpeg (for video processing)
- OpenAI API key
- Optional: Tesseract OCR

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd youtube-slide-summarizer
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg:**
   
   **macOS (using Homebrew):**
   ```bash
   brew install ffmpeg
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install ffmpeg
   ```
   
   **Windows:**
   Download from [FFmpeg website](https://ffmpeg.org/download.html)

5. **Optional - Install Tesseract OCR:**
   
   **macOS:**
   ```bash
   brew install tesseract
   ```
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt install tesseract-ocr
   ```

6. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

## Quick Start

```bash
# Initialize with your API key (first time only)
video-extract init

# Basic usage with video ID (recommended)
video-extract slides VIDEO_ID

# Or use full URL (remember to quote it)
video-extract slides "https://www.youtube.com/watch?v=VIDEO_ID"

# Generate JSON output
video-extract slides VIDEO_ID --output-format json

# Custom scene detection threshold
video-extract slides "https://youtu.be/VIDEO_ID" --scene-threshold 0.2

# Dry run (no API calls)
video-extract slides VIDEO_ID --dry-run

# Edit configuration
video-extract config
```

## Usage Examples

### Process a Technical Presentation
```bash
video-extract slides "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --output-format markdown \
  --scene-threshold 0.3 \
  --max-slides 50
```

### Generate JSON Data for API Integration
```bash
video-extract slides VIDEO_ID \
  --output-format json \
  --no-ocr \
  --output-dir ./reports
```

### Process Non-English Content
```bash
python cli.py VIDEO_ID \
  --language es \
  --output-format markdown
```

### Development/Testing Mode
```bash
python cli.py VIDEO_ID \
  --dry-run \
  --log-level DEBUG \
  --keep-temp
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional customizations
OPENAI_MODEL=gpt-4-vision-preview
SCENE_THRESHOLD=0.3
MAX_SLIDES=100
LOG_LEVEL=INFO
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-format` | Output format (markdown/json) | markdown |
| `--scene-threshold` | Scene detection sensitivity (0.1-1.0) | 0.3 |
| `--language` | Transcript language code | en |
| `--max-slides` | Maximum slides to extract | 100 |
| `--dry-run` | Skip API calls for testing | false |
| `--no-ocr` | Disable OCR text extraction | false |
| `--no-vision` | Use text-only summarization | false |
| `--keep-temp` | Keep temporary files | false |
| `--log-level` | Logging verbosity | INFO |

## Output

The tool generates comprehensive reports containing:

- **Slide Images**: Extracted key frames from the video
- **Timestamps**: Precise timing for each slide
- **Transcripts**: Aligned speech content for each slide
- **OCR Text**: Text detected on slides (if enabled)
- **AI Summaries**: Generated titles, summaries, and key points
- **Topics**: Extracted themes and topics
- **Metadata**: Processing statistics and configuration

### Sample Output Structure

```
outputs/
├── VIDEO_ID.md          # Markdown report
├── VIDEO_ID.json        # JSON data
└── index.md             # Index of all processed videos

slides/
└── VIDEO_ID/
    ├── slide_0001_15.30s.png
    ├── slide_0002_45.60s.png
    └── ...

transcripts/
└── VIDEO_ID.json        # Raw transcript data
```

## Advanced Usage

### Custom Processing Pipeline

```python
from src.config import Config
from src.downloader import TranscriptDownloader
from src.slides import SlideExtractor
from src.aligner import TranscriptSlideAligner
from src.summarizer import SlideSummarizer

# Initialize components
config = Config()
downloader = TranscriptDownloader(config)
slide_extractor = SlideExtractor(config)
# ... continue with custom processing
```

### Batch Processing

```bash
# Process multiple videos
for video_id in VIDEO_ID1 VIDEO_ID2 VIDEO_ID3; do
    python cli.py $video_id --output-format json
done
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**
   ```bash
   # Verify FFmpeg installation
   ffmpeg -version
   # If not found, install using package manager
   ```

2. **OpenAI API errors**
   ```bash
   # Check API key
   echo $OPENAI_API_KEY
   # Verify API quota and model access
   ```

3. **Transcript not available**
   - Some videos don't have transcripts
   - Try different language codes
   - Check if video is public

4. **Memory issues with large videos**
   ```bash
   # Reduce max slides
   python cli.py VIDEO_ID --max-slides 20
   # Use lower scene threshold
   python cli.py VIDEO_ID --scene-threshold 0.5
   ```

### Debug Mode

```bash
python cli.py VIDEO_ID --log-level DEBUG --dry-run
```

## Development

### Project Structure

```
youtube-slide-summarizer/
├── cli.py                    # Main entry point
├── src/
│   ├── config.py            # Configuration management
│   ├── downloader.py        # Transcript downloading
│   ├── slides.py            # Slide extraction
│   ├── aligner.py           # Content alignment
│   ├── ocr.py               # OCR processing
│   ├── summarizer.py        # AI summarization
│   ├── output.py            # Report generation
│   └── utils/
│       ├── logger.py        # Logging utilities
│       └── ffmpeg_wrapper.py # FFmpeg operations
├── tests/                   # Test files
├── requirements.txt         # Dependencies
└── README.md               # This file
```

### Running Tests

```bash
python -m pytest tests/ -v
```

### Code Quality

```bash
# Format code
python -m black src/ cli.py

# Lint code
python -m flake8 src/ cli.py

# Type checking
python -m mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT models
- FFmpeg project for video processing
- YouTube Transcript API contributors
- yt-dlp project for video downloading

## Support

If you encounter issues or have questions:

1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with:
   - Your OS and Python version
   - Complete error messages
   - Video URL (if public)
   - Command used

---

**Happy slide summarizing! 🎯**