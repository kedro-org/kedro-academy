"""Pydantic models for screening pipeline."""

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    """Requirement match result."""

    requirement: str = Field(description="Matched requirement")
    requirement_type: str = Field(description="Requirement type: 'must_have' or 'nice_to_have'")
    snippet_ids: list[str] = Field(description="Matching snippet IDs")
    confidence: float = Field(ge=0.0, le=1.0, description="Match confidence score")


class RequirementsMatchingMetadata(BaseModel):
    """Metadata for requirements matching result."""

    total_must_have_requirements: int = Field(description="Total number of must-have requirements")
    total_nice_to_have_requirements: int = Field(description="Total number of nice-to-have requirements")


class RequirementsMatchingResult(BaseModel):
    """Complete requirements matching result."""

    application_id: str = Field(description="Application identifier")
    candidate_name: str = Field(description="Candidate name")
    job_title: str = Field(description="Job title")
    match_results: list[MatchResult] = Field(description="List of match results")
    metadata: RequirementsMatchingMetadata = Field(description="Metadata with total requirement counts")


class ScoringResult(BaseModel):
    """Scoring tool result."""

    match_score: float = Field(ge=0.0, le=100.0, description="Overall match score (0-100)")
    must_have_coverage: float = Field(ge=0.0, le=1.0, description="Must-have requirements coverage (0-1)")
    must_have_matches: int = Field(ge=0, description="Number of matched must-have requirements")
    total_matches: int = Field(ge=0, description="Total number of matched requirements")


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
