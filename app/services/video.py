from pathlib import Path
import subprocess


def cut_clip(input_video: Path, start: float, end: float, output_path: Path) -> None:
    duration = max(0.0, end - start)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(input_video),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
