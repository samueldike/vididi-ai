import json
from typing import Any
from openai import OpenAI
from app.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    MAX_SHORTS,
    MIN_SHORT_SECONDS,
    MAX_SHORT_SECONDS,
)
from app.models.clip import ClipSelection


class GroqClipSelector:
    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing. Set it in .env")
        self.client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

    def _build_prompt(self, segments: list[dict], target_clips: int) -> str:
        transcript = "\n".join(
            [f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in segments]
        )
        return (
            "You are an expert short-form video editor for church sermons. "
            "Pick the most viral-worthy moments that can stand alone and remain faithful to message context.\\n"
            f"Return ONLY valid JSON with this schema: {{\"clips\":[{{\"start\":number,\"end\":number,\"title\":string,\"hook\":string,\"reason\":string}}]}}\\n"
            f"Select exactly {target_clips} clips.\\n"
            f"Each clip must be between {MIN_SHORT_SECONDS} and {MAX_SHORT_SECONDS} seconds.\\n"
            "Rules:\\n"
            "- Avoid cutting mid-sentence.\\n"
            "- Avoid overlap between selected clips.\\n"
            "- Ensure each clip has clear emotional or practical takeaway.\\n"
            "- Keep language concise and social-friendly.\\n"
            "Transcript follows:\\n"
            f"{transcript}"
        )

    def select(self, segments: list[dict], target_clips: int = MAX_SHORTS) -> list[dict[str, Any]]:
        prompt = self._build_prompt(segments, target_clips)
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        parsed = ClipSelection.model_validate(json.loads(content))
        normalized: list[dict[str, Any]] = []
        for clip in parsed.clips:
            if clip.end <= clip.start:
                continue
            dur = clip.end - clip.start
            if dur < MIN_SHORT_SECONDS or dur > MAX_SHORT_SECONDS:
                continue
            normalized.append(clip.model_dump())
        return normalized
