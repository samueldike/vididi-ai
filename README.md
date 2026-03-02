# vid-trim (Groq + Whisper)

Long-form to short-form sermon clipper using private STT + LLM-assisted clip selection.

## What it does
- Transcribes long audio/video with `faster-whisper`
- Uses Groq API (OpenAI-compatible) to select viral-ready short segments
- Accepts either uploaded file or YouTube URL input
- Enforces configurable max clip duration (default 30 seconds)
- Outputs TikTok/Reels-ready vertical `9:16` clips (1080x1920 default)
- Burns captions directly into each output clip
- Writes detailed per-job logs and processing metrics for troubleshooting
- Cuts final MP4 clips with FFmpeg
- Includes simple web UI for non-technical staff

## Requirements
- Python 3.10+
- FFmpeg installed and available on PATH (with subtitles/libass support)
- Groq API key
- `yt-dlp` (installed by requirements)

## Setup
```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

Create `.env` in project root:
```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1
WHISPER_MODEL=large-v3
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
MAX_SHORTS=5
MIN_SHORT_SECONDS=15
MAX_SHORT_SECONDS=30
OUTPUT_WIDTH=1080
OUTPUT_HEIGHT=1920
CAPTION_FONT_SIZE=18
LOG_LEVEL=INFO
```

## Run App (API + Web UI)
```bash
uvicorn app.main:app --reload --port 8000
```
Open UI: `http://127.0.0.1:8000/`

## UI Flow
1. Upload sermon file or paste YouTube URL
2. Choose number of short clips (1-10)
3. Set max duration per clip (10-120s, default 30s)
4. Click **Generate Short Clips**
5. Preview/download each generated clip

## API
Open docs: `http://127.0.0.1:8000/docs`
Use `POST /process` with multipart form:
- `file` (optional)
- `youtube_url` (optional)
- plus query params `clips` and `max_seconds`

At least one of `file` or `youtube_url` is required.
`POST /process` is async and returns immediately with:
- `status_url` (`/jobs/{job_id}/status`)
- `result_url` (`/jobs/{job_id}/result`)
- `log_url` (`/jobs/{job_id}/log`)

### Logs and tracking
- Per-job detailed log: `GET /jobs/{job_id}/log`
- Per-job status: `GET /jobs/{job_id}/status`
- Per-job final result: `GET /jobs/{job_id}/result`
- JSON log file path: `outputs/{job_id}/job.log.jsonl`
- Job summary/metrics path: `outputs/{job_id}/job.meta.json`

## Run CLI
```bash
python scripts/run_pipeline.py path/to/sermon.mp4 --out outputs/sermon01 --clips 5
```

## Deploy cheaply (VPS)
- GPU optional: if no GPU, keep `WHISPER_COMPUTE_TYPE=int8` for CPU mode (slower).
- Cheapest practical online path: RunPod spot GPU + this app as Docker/VM process.
- For strict privacy and low cost: process batch on-demand (not 24/7 uptime).
