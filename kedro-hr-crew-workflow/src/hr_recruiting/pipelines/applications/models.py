"""Pydantic models for applications pipeline."""

from typing import Any

from pydantic import BaseModel, Field


class WorkHistory(BaseModel):
    """Work history entry."""

    company: str
    role: str
    duration: str
    description: str


class Education(BaseModel):
    """Education entry."""

    institution: str
    degree: str
    field: str | None = None
    year: str | None = None


class CandidateProfile(BaseModel):
    """Candidate profile model."""

    candidate_id: str = Field(description="Unique candidate identifier")
    name: str = Field(description="Candidate name")
    email: str = Field(description="Candidate email")
    skills: list[str] = Field(default_factory=list, description="List of skills")
    work_history: list[WorkHistory] = Field(default_factory=list, description="Work history")
    education: list[Education] = Field(default_factory=list, description="Education background")
    raw_resume_text: str = Field(description="Raw resume text")


class EvidenceSnippet(BaseModel):
    """Evidence snippet for matching."""

    snippet_id: str = Field(description="Unique snippet identifier")
    text: str = Field(description="Snippet text")
    source: str = Field(description="Source field (e.g., 'work_history', 'skills')")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
