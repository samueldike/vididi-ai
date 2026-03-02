# vid-trim (Groq + Whisper)

Long-form to short-form sermon clipper using private STT + LLM-assisted clip selection.

## What it does
- Transcribes long audio/video with `faster-whisper`
- Uses Groq API (OpenAI-compatible) to select viral-ready short segments
- Cuts final MP4 clips with FFmpeg
- Includes simple web UI for non-technical staff

## Requirements
- Python 3.10+
- FFmpeg installed and available on PATH
- Groq API key

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
MIN_SHORT_SECONDS=25
MAX_SHORT_SECONDS=60
```

## Run App (API + Web UI)
```bash
uvicorn app.main:app --reload --port 8000
```
Open UI: `http://127.0.0.1:8000/`

## UI Flow
1. Upload sermon audio/video file
2. Choose number of short clips (1-10)
3. Click **Generate Short Clips**
4. Preview/download each generated clip

## API
Open docs: `http://127.0.0.1:8000/docs`
Use `POST /process` with media file + optional `clips` query.

## Run CLI
```bash
python scripts/run_pipeline.py path/to/sermon.mp4 --out outputs/sermon01 --clips 5
```

## Deploy cheaply (VPS)
- GPU optional: if no GPU, keep `WHISPER_COMPUTE_TYPE=int8` for CPU mode (slower).
- Cheapest practical online path: RunPod spot GPU + this app as Docker/VM process.
- For strict privacy and low cost: process batch on-demand (not 24/7 uptime).
