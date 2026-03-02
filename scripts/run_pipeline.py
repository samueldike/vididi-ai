import argparse
import json
from pathlib import Path
from app.services.stt import STTService
from app.services.llm_selector import GroqClipSelector
from app.services.video import cut_clip


def run(input_file: Path, out_dir: Path, clips: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    stt = STTService()
    selector = GroqClipSelector()

    segments = stt.transcribe(input_file)
    selected = selector.select(segments, target_clips=clips)

    manifest = []
    for i, clip in enumerate(selected, start=1):
        out_path = out_dir / f"clip_{i:02}.mp4"
        cut_clip(input_file, clip["start"], clip["end"], out_path)
        manifest.append({**clip, "file": str(out_path)})

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} clips in {out_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("outputs/manual"))
    parser.add_argument("--clips", type=int, default=5)
    args = parser.parse_args()
    run(args.input, args.out, args.clips)
