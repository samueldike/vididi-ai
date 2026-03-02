from pathlib import Path
import subprocess


def download_youtube_video(url: str, output_dir: Path, stem: str) -> Path:
    output_template = str(output_dir / f"{stem}.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f",
        "mp4/bestvideo+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    matches = sorted(output_dir.glob(f"{stem}.*"))
    if not matches:
        raise RuntimeError("YouTube download failed: no output file found")
    return matches[0]
