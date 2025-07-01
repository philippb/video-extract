
# YouTube Slide Summarizer CLI – High‑Level Implementation Plan

## 1. Objective
Create a local Python CLI tool that ingests a YouTube URL, retrieves the video’s transcript and slide images, aligns them, and produces GPT‑4‑generated slide summaries.

---

## 2. Proposed Project Structure
```
youtube‑slide‑summarizer/
├── README.md
├── requirements.txt
├── cli.py                 # Entry point
├── .env.example           # Sample env file
├── src/
│   ├── __init__.py
│   ├── config.py          # Env & runtime config
│   ├── downloader.py      # Transcript retrieval
│   ├── slides.py          # Slide/key‑frame extraction
│   ├── aligner.py         # Transcript‑to‑slide alignment
│   ├── ocr.py             # Slide OCR (optional)
│   ├── summarizer.py      # OpenAI calls
│   ├── output.py          # Report generation
│   └── utils/
│       ├── logger.py
│       └── ffmpeg_wrapper.py
└── tests/
    └── ...
```

---

## 3. Module Responsibilities

### 3.1 `cli.py`
- Parse command‑line arguments (`argparse`).
- Validate inputs and environment (API key, ffmpeg).
- Orchestrate the end‑to‑end pipeline.
- Global flags: `--dry‑run`, `--output‑format`, `--scene‑threshold`, `--language`.

### 3.2 `config.py`
- Load variables from environment or `.env`.
- Central place for defaults (model name, max tokens, retry counts).

### 3.3 `downloader.py`
- Attempt official YouTube transcript via `youtube‑transcript‑api`.
- Fallback: use `yt‑dlp` to fetch auto‑generated subtitles.
- Normalize transcript into `{start, end, text}` items.
- Persist raw and cleaned transcripts under `transcripts/`.

### 3.4 `slides.py`
- Invoke `ffmpeg` with scene‑change detection to extract candidate frames.
- Post‑process to remove near‑duplicates (hash comparison).
- Output: list of `{timestamp, image_path}`.

### 3.5 `aligner.py`
- For each slide timestamp, gather transcript sentences that fall between this timestamp and the next slide.
- Return list of slide objects containing `image`, `ocr_text` (optional), `transcript_chunk`.

### 3.6 `ocr.py` (optional)
- If slide text is important, run Tesseract on each image.
- Pre‑clean images (grayscale, threshold) for OCR accuracy.
- Allow bypass when GPT‑4 Vision will be used directly.

### 3.7 `summarizer.py`
- Compose prompt with slide OCR (or raw image) + transcript chunk.
- Call OpenAI ChatCompletion endpoint.
- Handle streaming, rate‑limit retries, exponential backoff.
- Append model output (`summary`, `title`, etc.) to slide object.

### 3.8 `output.py`
- Assemble final report in chosen format:
  - **Markdown**: embed image links, transcript, summary.
  - **JSON**: structured for downstream consumption.
- Save under `outputs/{video_id}.{md|json}`.

### 3.9 `utils/`
- **`logger.py`**: Standardized logging with verbosity levels.
- **`ffmpeg_wrapper.py`**: Helper to build/run `ffmpeg` commands and parse output.

---

## 4. End‑to‑End Pipeline Flow
1. **Init**: `cli.py` parses args, loads config, checks prerequisites.
2. **Download Transcript**: `downloader.py` → `transcripts/`.
3. **Extract Slides**: `slides.py` → `slides/`.
4. **Align**: `aligner.py` produces in‑memory slide objects.
5. **(Optional) OCR**: `ocr.py` enriches slide objects with detected text.
6. **Summarize**: `summarizer.py` sends each slide to OpenAI, collects responses.
7. **Output**: `output.py` writes final file(s); CLI prints summary path.

---

## 5. Error Handling & Edge Cases
- **No Transcript**: Notify user and abort gracefully.
- **No Slides Detected**: Fallback to fixed‑interval frame capture.
- **OpenAI Errors**: Implement retry w/ exponential backoff; support `--dry‑run`.
- **Long Videos**: Allow chunking or slide‑range selection.

---

## 6. Testing Strategy
- Unit tests per module (mock external calls).
- Integration test with a short public video fixture.
- CLI smoke test in CI (GitHub Actions).

---

## 7. Installation & Usage
```bash
# Install deps
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run
python cli.py https://www.youtube.com/watch?v=VIDEO_ID     --output-format markdown --scene-threshold 0.3
```

---

## 8. Potential Extensions
- Multi‑language transcript auto‑translation.
- Local Whisper transcription fallback.
- Batch‑mode processing (multiple URLs).
- GUI wrapper (desktop or web).
- Cache to avoid re‑processing slides.

---

*(No implementation code included — this file is strictly a high‑level blueprint.)*
