from pathlib import Path
import subprocess


def _subtitle_filter_path(path: Path) -> str:
    p = str(path.resolve()).replace("\\", "/")
    return p.replace(":", "\\:").replace("'", "\\'")


def cut_clip(
    input_video: Path,
    start: float,
    end: float,
    output_path: Path,
    width: int,
    height: int,
    srt_path: Path | None = None,
    caption_font_size: int = 18,
) -> None:
    duration = max(0.0, end - start)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    if srt_path and srt_path.exists():
        subs_path = _subtitle_filter_path(srt_path)
        style = f"FontName=Arial,FontSize={caption_font_size},PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=45"
        vf = f"{vf},subtitles='{subs_path}':force_style='{style}'"
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(input_video),
        "-t",
        str(duration),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
