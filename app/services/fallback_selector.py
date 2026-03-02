def select_fallback_clips(
    segments: list[dict],
    target_clips: int,
    min_seconds: int,
    max_seconds: int,
) -> list[dict]:
    # Score segments by text length and greedily build non-overlapping windows.
    ranked = sorted(segments, key=lambda s: len(s.get("text", "").strip()), reverse=True)
    picks: list[dict] = []

    def overlaps(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
        return not (a_end <= b_start or b_end <= a_start)

    for seg in ranked:
        if len(picks) >= target_clips:
            break
        center = (float(seg["start"]) + float(seg["end"])) / 2.0
        start = max(0.0, center - (max_seconds / 2.0))
        end = start + max_seconds
        if end - start < min_seconds:
            end = start + min_seconds
        clash = any(overlaps(start, end, p["start"], p["end"]) for p in picks)
        if clash:
            continue
        text = seg.get("text", "").strip()
        picks.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "title": (text[:55] + "...") if len(text) > 58 else text or "Key sermon moment",
                "hook": text[:120] or "Powerful message excerpt",
                "reason": "Fallback selection based on transcript density.",
            }
        )
    return sorted(picks, key=lambda x: x["start"])
