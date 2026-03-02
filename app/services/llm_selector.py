import json
from typing import Any
from openai import OpenAI
from app.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    MAX_SHORTS,
)
from app.models.clip import ClipSelection


class GroqClipSelector:
    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing. Set it in .env")
        self.client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)

    def _build_prompt(
        self,
        segments: list[dict],
        target_clips: int,
        min_seconds: int,
        max_seconds: int,
    ) -> str:
        transcript = "\n".join(
            [f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}" for s in segments]
        )
        return (
            "You are an expert short-form video editor for church sermons. "
            "Pick the most viral-worthy moments that can stand alone and remain faithful to message context.\\n"
            f"Return ONLY valid JSON with this schema: {{\"clips\":[{{\"start\":number,\"end\":number,\"title\":string,\"hook\":string,\"reason\":string}}]}}\\n"
            f"Select exactly {target_clips} clips.\\n"
            f"Each clip must be between {min_seconds} and {max_seconds} seconds.\\n"
            "Rules:\\n"
            "- Avoid cutting mid-sentence.\\n"
            "- Avoid overlap between selected clips.\\n"
            "- Ensure each clip has clear emotional or practical takeaway.\\n"
            "- Keep language concise and social-friendly.\\n"
            "Transcript follows:\\n"
            f"{transcript}"
        )

    def select(
        self,
        segments: list[dict],
        target_clips: int = MAX_SHORTS,
        min_seconds: int = 15,
        max_seconds: int = 30,
    ) -> list[dict[str, Any]]:
        prompt = self._build_prompt(segments, target_clips, min_seconds, max_seconds)
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
            if dur < min_seconds or dur > max_seconds:
                continue
            normalized.append(clip.model_dump())
        return normalized
