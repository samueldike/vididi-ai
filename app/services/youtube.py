from pathlib import Path
import subprocess
from urllib.parse import urlparse


def _normalize_youtube_url(url: str) -> str:
    # Convert youtube.com/live/<id> style URLs to watch URLs for better yt-dlp compatibility.
    try:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "youtube.com" in parsed.netloc and len(parts) >= 2 and parts[0] == "live":
            return f"https://www.youtube.com/watch?v={parts[1]}"
    except Exception:
        pass
    return url


def download_youtube_video(url: str, output_dir: Path, stem: str) -> Path:
    normalized_url = _normalize_youtube_url(url)
    output_template = str(output_dir / f"{stem}.%(ext)s")

    # Try robust format strategy first, then fallback selector.
    cmd_variants = [
        [
            "yt-dlp",
            "--no-playlist",
            "--force-ipv4",
            "--extractor-args",
            "youtube:player_client=android,web",
            "-f",
            "bv*+ba/b",
            "--remux-video",
            "mp4",
            "-o",
            output_template,
            normalized_url,
        ],
        [
            "yt-dlp",
            "--no-playlist",
            "--force-ipv4",
            "-f",
            "best",
            "--remux-video",
            "mp4",
            "-o",
            output_template,
            normalized_url,
        ],
    ]

    last_err = ""
    for cmd in cmd_variants:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            last_err = ""
            break
        last_err = (proc.stderr or proc.stdout or "").strip()

    if last_err:
        raise RuntimeError(
            "yt-dlp failed. "
            "This video may require login/cookies, be geoblocked, private, or currently unavailable. "
            f"Details: {last_err[:1200]}"
        )

    matches = sorted(output_dir.glob(f"{stem}.*"))
    if not matches:
        raise RuntimeError("YouTube download failed: no output file found")
    return matches[0]
