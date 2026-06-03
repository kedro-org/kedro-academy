"""Consumer Marketing evaluation models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeScore(BaseModel):
    """LLM-judge output for one consumer offer message.

    Dimensions: offer relevance, personalisation, urgency/CTA, tone, compliance.
    """

    offer_relevance: float = Field(..., ge=0.0, le=1.0)
    offer_relevance_reason: str
    personalisation: float = Field(..., ge=0.0, le=1.0)
    personalisation_reason: str
    urgency_cta: float = Field(..., ge=0.0, le=1.0)
    urgency_cta_reason: str
    tone: float = Field(..., ge=0.0, le=1.0)
    tone_reason: str
    compliance: float = Field(..., ge=0.0, le=1.0)
    compliance_reason: str
