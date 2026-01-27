"""Pydantic models for screening pipeline."""

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    """Requirement match result."""

    requirement: str = Field(description="Matched requirement")
    requirement_type: str = Field(description="Requirement type: 'must_have' or 'nice_to_have'")
    snippet_ids: list[str] = Field(description="Matching snippet IDs")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence score")


class ScreeningResult(BaseModel):
    """Screening result model."""

    application_id: str = Field(description="Application identifier")
    candidate_name: str = Field(description="Candidate name for communications")
    job_title: str = Field(description="Job title for communications")
    match_score: float = Field(ge=0.0, le=100.0, description="Overall match score (0-100)")
    must_have_coverage: float = Field(ge=0.0, le=1.0, description="Must-have requirements coverage")
    gaps: list[str] = Field(default_factory=list, description="Identified gaps")
    strengths: list[str] = Field(default_factory=list, description="Candidate strengths")
    risk_flags: list[str] = Field(default_factory=list, description="Risk flags")
    recommendation: str = Field(description="Recommendation (e.g., 'proceed', 'reject', 'review')")
    qa_suggestions: list[str] = Field(default_factory=list, description="QA suggestions")
    match_results: list[MatchResult] = Field(default_factory=list, description="Detailed match results")
