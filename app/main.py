from pathlib import Path
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import (
    UPLOAD_DIR,
    OUTPUT_DIR,
    MAX_SHORTS,
    MIN_SHORT_SECONDS,
    MAX_SHORT_SECONDS,
    OUTPUT_WIDTH,
    OUTPUT_HEIGHT,
    CAPTION_FONT_SIZE,
)
from app.services.stt import STTService
from app.services.llm_selector import GroqClipSelector
from app.services.video import cut_clip
from app.services.youtube import download_youtube_video
from app.services.captions import write_clip_srt

app = FastAPI(title="vid-trim", version="0.1.0")
stt = STTService()
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/jobs/{job_id}/{filename}")
def get_job_file(job_id: str, filename: str) -> FileResponse:
    target = (OUTPUT_DIR / job_id / filename).resolve()
    expected_parent = (OUTPUT_DIR / job_id).resolve()
    if target.parent != expected_parent or not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(target)


@app.post("/process")
async def process(
    file: UploadFile | None = File(default=None),
    youtube_url: str | None = Form(default=None),
    clips: int = MAX_SHORTS,
    max_seconds: int = MAX_SHORT_SECONDS,
) -> dict:
    if clips < 1 or clips > 10:
        raise HTTPException(status_code=400, detail="clips must be 1-10")
    if max_seconds < 10 or max_seconds > 120:
        raise HTTPException(status_code=400, detail="max_seconds must be 10-120")
    min_seconds = min(MIN_SHORT_SECONDS, max_seconds)

    try:
        selector = GroqClipSelector()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    if file is None and not youtube_url:
        raise HTTPException(status_code=400, detail="Provide a file upload or youtube_url")

    if youtube_url:
        try:
            input_path = download_youtube_video(youtube_url, UPLOAD_DIR, f"{job_id}_youtube")
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"YouTube download failed: {exc}") from exc
    else:
        input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with input_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)

    segments = stt.transcribe(input_path)
    if not segments:
        raise HTTPException(status_code=422, detail="No speech detected")

    chosen = selector.select(
        segments,
        target_clips=clips,
        min_seconds=min_seconds,
        max_seconds=max_seconds,
    )
    outputs = []
    for idx, clip in enumerate(chosen, start=1):
        if clip["end"] > clip["start"] + max_seconds:
            clip["end"] = clip["start"] + max_seconds
        out_name = f"clip_{idx:02}.mp4"
        out_file = job_dir / out_name
        srt_path = job_dir / f"clip_{idx:02}.srt"
        write_clip_srt(segments, clip["start"], clip["end"], srt_path)
        cut_clip(
            input_path,
            clip["start"],
            clip["end"],
            out_file,
            width=OUTPUT_WIDTH,
            height=OUTPUT_HEIGHT,
            srt_path=srt_path,
            caption_font_size=CAPTION_FONT_SIZE,
        )
        outputs.append({
            "file": str(out_file),
            "url": f"/jobs/{job_id}/{out_name}",
            "start": clip["start"],
            "end": clip["end"],
            "title": clip["title"],
            "hook": clip["hook"],
            "reason": clip["reason"],
        })

    return {
        "job_id": job_id,
        "clips": outputs,
        "transcript_segments": len(segments),
    }
