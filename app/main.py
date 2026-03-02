import logging
from pathlib import Path
import shutil
import time
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
    LOG_LEVEL,
)
from app.services.stt import STTService
from app.services.llm_selector import GroqClipSelector
from app.services.video import cut_clip
from app.services.youtube import download_youtube_video
from app.services.captions import write_clip_srt
from app.services.job_logger import JobLogger

app = FastAPI(title="vid-trim", version="0.1.0")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("vidtrim")
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


@app.get("/jobs/{job_id}/log")
def get_job_log(job_id: str) -> FileResponse:
    target = (OUTPUT_DIR / job_id / "job.log.jsonl").resolve()
    expected_parent = (OUTPUT_DIR / job_id).resolve()
    if target.parent != expected_parent or not target.exists():
        raise HTTPException(status_code=404, detail="Log not found")
    return FileResponse(target)


@app.post("/process")
async def process(
    file: UploadFile | None = File(default=None),
    youtube_url: str | None = Form(default=None),
    clips: int = MAX_SHORTS,
    max_seconds: int = MAX_SHORT_SECONDS,
) -> dict:
    started_at = time.perf_counter()
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
    joblog = JobLogger(job_id=job_id, job_dir=job_dir)
    joblog.event("start", "job created", clips=clips, max_seconds=max_seconds)

    if file is None and not youtube_url:
        joblog.event("input", "missing input")
        raise HTTPException(status_code=400, detail="Provide a file upload or youtube_url")

    try:
        t0 = time.perf_counter()
        if youtube_url:
            joblog.event("input", "downloading youtube", youtube_url=youtube_url)
            input_path = download_youtube_video(youtube_url, UPLOAD_DIR, f"{job_id}_youtube")
            joblog.event("input", "youtube download complete", path=str(input_path))
        else:
            input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
            with input_path.open("wb") as out:
                shutil.copyfileobj(file.file, out)
            joblog.event("input", "upload saved", filename=file.filename, path=str(input_path))
        input_seconds = time.perf_counter() - t0

        t1 = time.perf_counter()
        segments = stt.transcribe(input_path)
        stt_seconds = time.perf_counter() - t1
        if not segments:
            joblog.event("stt", "no speech detected")
            raise HTTPException(status_code=422, detail="No speech detected")
        transcript_start = min(s["start"] for s in segments)
        transcript_end = max(s["end"] for s in segments)
        transcript_duration = max(0.0, transcript_end - transcript_start)
        speech_duration = sum(max(0.0, s["end"] - s["start"]) for s in segments)
        speech_ratio = (speech_duration / transcript_duration) if transcript_duration > 0 else 0.0
        joblog.event(
            "stt",
            "transcription complete",
            segment_count=len(segments),
            transcript_duration=round(transcript_duration, 2),
            speech_duration=round(speech_duration, 2),
            speech_ratio=round(speech_ratio, 4),
            elapsed_seconds=round(stt_seconds, 2),
        )

        t2 = time.perf_counter()
        chosen = selector.select(
            segments,
            target_clips=clips,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
        )
        llm_seconds = time.perf_counter() - t2
        joblog.event("llm", "clip selection complete", selected_count=len(chosen), elapsed_seconds=round(llm_seconds, 2))

        t3 = time.perf_counter()
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
            clip_duration = round(max(0.0, clip["end"] - clip["start"]), 2)
            joblog.event("render", "clip rendered", index=idx, file=out_name, duration=clip_duration)
            outputs.append({
                "file": str(out_file),
                "url": f"/jobs/{job_id}/{out_name}",
                "start": clip["start"],
                "end": clip["end"],
                "title": clip["title"],
                "hook": clip["hook"],
                "reason": clip["reason"],
                "duration": clip_duration,
            })
        render_seconds = time.perf_counter() - t3
        total_seconds = time.perf_counter() - started_at
        joblog.write_meta(
            job_id=job_id,
            source=str(input_path),
            transcript_segments=len(segments),
            selected_clips=len(outputs),
            elapsed_seconds=round(total_seconds, 2),
            stage_seconds={
                "input": round(input_seconds, 2),
                "stt": round(stt_seconds, 2),
                "llm": round(llm_seconds, 2),
                "render": round(render_seconds, 2),
            },
            accuracy_proxy={
                "speech_ratio": round(speech_ratio, 4),
                "transcript_duration": round(transcript_duration, 2),
                "speech_duration": round(speech_duration, 2),
            },
        )
        joblog.event("done", "job complete", elapsed_seconds=round(total_seconds, 2))
        logger.info("job complete job_id=%s clips=%s total_seconds=%.2f", job_id, len(outputs), total_seconds)

        return {
            "job_id": job_id,
            "clips": outputs,
            "transcript_segments": len(segments),
            "metrics": {
                "elapsed_seconds": round(total_seconds, 2),
                "stage_seconds": {
                    "input": round(input_seconds, 2),
                    "stt": round(stt_seconds, 2),
                    "llm": round(llm_seconds, 2),
                    "render": round(render_seconds, 2),
                },
                "accuracy_proxy": {
                    "speech_ratio": round(speech_ratio, 4),
                    "transcript_duration": round(transcript_duration, 2),
                    "speech_duration": round(speech_duration, 2),
                },
            },
            "log_url": f"/jobs/{job_id}/log",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("job failed job_id=%s", job_id)
        joblog.event("error", "job failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Processing failed. job_id={job_id}. Check log at /jobs/{job_id}/log") from exc
