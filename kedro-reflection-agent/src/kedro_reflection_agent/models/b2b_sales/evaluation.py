"""B2B Sales evaluation models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    """LLM-judge output for one B2B outreach email.

    Dimensions: writing quality, personalisation depth, groundedness.
    """

    writing_quality: float = Field(..., ge=0.0, le=1.0)
    writing_quality_reason: str
    personalization: float = Field(..., ge=0.0, le=1.0)
    personalization_reason: str
    groundedness: float = Field(..., ge=0.0, le=1.0)
    groundedness_reason: str
