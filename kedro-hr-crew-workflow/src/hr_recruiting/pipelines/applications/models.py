"""Pydantic models for applications pipeline."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ParsedResume(BaseModel):
    """Parsed resume model containing extracted text and candidate ID."""

    candidate_id: str = Field(description="Candidate identifier from document properties")
    raw_resume_text: str = Field(description="Extracted raw resume text")


class EvidenceSnippet(BaseModel):
    """Evidence snippet for matching."""

    snippet_id: str = Field(description="Unique snippet identifier")
    text: str = Field(description="Snippet text")
    source: str = Field(description="Source field (e.g., 'work_history', 'skills')")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class Application(BaseModel):
    """Application model linking candidate to job."""

    application_id: str = Field(description="Unique application identifier")
    candidate_id: str = Field(description="Candidate identifier")
    candidate_name: str = Field(description="Candidate name")
    submitted_at: datetime = Field(description="Submission timestamp")
    status: str = Field(default="pending", description="Application status")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Job-related artifacts (job_id, job_title, location)")
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list, description="Evidence snippets for matching")


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

