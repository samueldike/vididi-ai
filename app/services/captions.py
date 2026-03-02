from pathlib import Path


def _fmt_srt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    hrs = ms // 3_600_000
    rem = ms % 3_600_000
    mins = rem // 60_000
    rem %= 60_000
    secs = rem // 1000
    millis = rem % 1000
    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"


def write_clip_srt(segments: list[dict], clip_start: float, clip_end: float, srt_path: Path) -> None:
    lines: list[str] = []
    idx = 1
    for seg in segments:
        seg_start = max(seg["start"], clip_start)
        seg_end = min(seg["end"], clip_end)
        if seg_end <= seg_start:
            continue
        rel_start = seg_start - clip_start
        rel_end = seg_end - clip_start
        text = seg["text"].strip()
        if not text:
            continue
        lines.append(str(idx))
        lines.append(f"{_fmt_srt_time(rel_start)} --> {_fmt_srt_time(rel_end)}")
        lines.append(text)
        lines.append("")
        idx += 1
    srt_path.write_text("\n".join(lines), encoding="utf-8")
