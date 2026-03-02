from pydantic import BaseModel, Field


class ClipCandidate(BaseModel):
    start: float = Field(..., ge=0)
    end: float = Field(..., gt=0)
    title: str
    hook: str
    reason: str


class ClipSelection(BaseModel):
    clips: list[ClipCandidate]
