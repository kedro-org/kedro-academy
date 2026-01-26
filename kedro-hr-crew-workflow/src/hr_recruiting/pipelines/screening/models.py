"""Pydantic models for screening pipeline."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Application(BaseModel):
    """Application model."""

    application_id: str = Field(description="Unique application identifier")
    job_id: str = Field(description="Job identifier")
    candidate_id: str = Field(description="Candidate identifier")
    submitted_at: datetime = Field(description="Submission timestamp")
    status: str = Field(default="pending", description="Application status")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Additional artifacts")


class MatchResult(BaseModel):
    """Requirement match result."""

    requirement: str = Field(description="Matched requirement")
    snippet_ids: list[str] = Field(description="Matching snippet IDs")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence score")


class EmailDraft(BaseModel):
    """Email draft model."""

    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    placeholders: dict[str, str] = Field(default_factory=dict, description="Template placeholders")


class ScreeningResult(BaseModel):
    """Screening result model."""

    application_id: str = Field(description="Application identifier")
    match_score: float = Field(ge=0.0, le=100.0, description="Overall match score (0-100)")
    must_have_coverage: float = Field(ge=0.0, le=1.0, description="Must-have requirements coverage")
    gaps: list[str] = Field(default_factory=list, description="Identified gaps")
    strengths: list[str] = Field(default_factory=list, description="Candidate strengths")
    risk_flags: list[str] = Field(default_factory=list, description="Risk flags")
    recommendation: str = Field(description="Recommendation (e.g., 'proceed', 'reject', 'review')")
    email_draft: EmailDraft | None = Field(default=None, description="Drafted email")
    qa_suggestions: list[str] = Field(default_factory=list, description="QA suggestions")
    match_results: list[MatchResult] = Field(default_factory=list, description="Detailed match results")
