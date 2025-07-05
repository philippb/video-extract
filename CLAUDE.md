# video-extract

## Project Overview
**video-extract** is a Python CLI tool that extracts YouTube video transcripts and slide images, aligns them, and generates GPT-4 summaries of each slide.

## Key Features
- Extracts transcripts from YouTube videos using youtube-transcript-api and yt-dlp fallback
- Detects slide changes using ffmpeg scene detection
- Aligns transcript segments with slide timestamps
- Optional OCR for slide text extraction
- Generates AI-powered slide summaries using OpenAI API
- Outputs results in Markdown or JSON format

## Dependencies
- Python 3.8+
- ffmpeg (for video processing)
- OpenAI API key
- Optional: Tesseract OCR

## Installation
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Installation & Setup
```bash
# Via Homebrew (recommended)
brew install video-extract
video-extract init

# Or manual installation
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage
```bash
# Initialize with API key prompt (first time only)
video-extract init

# Edit configuration file
video-extract config

# Process videos
video-extract slides "https://www.youtube.com/watch?v=VIDEO_ID" --output-format markdown --scene-threshold 0.3
video-extract slides VIDEO_ID --max-slides 10
```

## Environment Variables
- `OPENAI_API_KEY`: Required for AI summarization
- `OPENAI_MODEL`: Model to use (default: gpt-4-vision-preview)
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Testing
```bash
python -m pytest tests/
```

## Linting
```bash
python -m flake8 src/ cli.py
python -m black src/ cli.py --check
```

## Project Structure
- `cli.py`: Main entry point
- `src/`: Core modules
  - `config.py`: Configuration management
  - `downloader.py`: Transcript downloading
  - `slides.py`: Slide extraction
  - `aligner.py`: Transcript-slide alignment
  - `ocr.py`: OCR functionality
  - `summarizer.py`: AI summarization
  - `output.py`: Report generation
  - `utils/`: Utility modules

## Output Directories
- `transcripts/`: Downloaded transcripts
- `slides/`: Extracted slide images
- `outputs/`: Final reports

## Claude's Development Guidelines
- NEVER git add and git commit things yourself without user consent