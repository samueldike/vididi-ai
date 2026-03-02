from pathlib import Path
from faster_whisper import WhisperModel
from app.config import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


class STTService:
    def __init__(self) -> None:
        self.model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    def transcribe(self, media_path: Path) -> list[dict]:
        segments, _info = self.model.transcribe(
            str(media_path),
            word_timestamps=False,
            vad_filter=True,
            beam_size=5,
        )
        out: list[dict] = []
        for s in segments:
            text = s.text.strip()
            if not text:
                continue
            out.append({"start": float(s.start), "end": float(s.end), "text": text})
        return out
