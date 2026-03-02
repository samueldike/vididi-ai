from pathlib import Path
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import UPLOAD_DIR, OUTPUT_DIR, MAX_SHORTS
from app.services.stt import STTService
from app.services.llm_selector import GroqClipSelector
from app.services.video import cut_clip

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
async def process(file: UploadFile = File(...), clips: int = MAX_SHORTS) -> dict:
    if clips < 1 or clips > 10:
        raise HTTPException(status_code=400, detail="clips must be 1-10")

    try:
        selector = GroqClipSelector()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    job_id = str(uuid.uuid4())
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    input_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    with input_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    segments = stt.transcribe(input_path)
    if not segments:
        raise HTTPException(status_code=422, detail="No speech detected")

    chosen = selector.select(segments, target_clips=clips)
    outputs = []
    for idx, clip in enumerate(chosen, start=1):
        out_name = f"clip_{idx:02}.mp4"
        out_file = job_dir / out_name
        cut_clip(input_path, clip["start"], clip["end"], out_file)
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
