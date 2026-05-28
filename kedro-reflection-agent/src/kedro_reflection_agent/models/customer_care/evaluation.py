"""Customer Care evaluation models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    """LLM-judge output for one customer care support reply.

    Dimensions: empathy opener, resolution clarity, tone, compliance,
    escalation avoidance.
    """

    empathy_opener: float = Field(..., ge=0.0, le=1.0)
    empathy_opener_reason: str
    resolution_clarity: float = Field(..., ge=0.0, le=1.0)
    resolution_clarity_reason: str
    tone: float = Field(..., ge=0.0, le=1.0)
    tone_reason: str
    compliance: float = Field(..., ge=0.0, le=1.0)
    compliance_reason: str
    escalation_avoidance: float = Field(..., ge=0.0, le=1.0)
    escalation_avoidance_reason: str
