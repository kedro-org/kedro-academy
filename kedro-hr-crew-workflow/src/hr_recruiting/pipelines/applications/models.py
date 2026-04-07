"""Pydantic models for applications pipeline."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

class ParsedResume(BaseModel):
    """Parsed resume model containing extracted text and candidate ID."""

    candidate_id: str = Field(description="Candidate identifier from document properties")
    raw_resume_text: str = Field(description="Extracted raw resume text")

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

class ResumeParsingOutput(BaseModel):
    """Expected output from resume parsing crew execution."""

    candidate_profile: CandidateProfile = Field(description="Extracted candidate profile")
    evidence_snippets: list[EvidenceSnippet] = Field(description="Evidence snippets for matching")

class Application(BaseModel):
    """Application model linking candidate to job.
    
    This model represents a candidate's application for a specific job position.
    It combines candidate information with job metadata and evidence snippets
    for use in the screening pipeline.
    """

    application_id: str = Field(description="Unique application identifier (format: candidate_id_job_id)")
    candidate_id: str = Field(description="Candidate identifier")
    candidate_name: str = Field(description="Candidate name")
    submitted_at: datetime = Field(description="Submission timestamp")
    status: str = Field(default="pending", description="Application status")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="Job-related artifacts containing job_id, job_title, and location")
    evidence_snippets: list[EvidenceSnippet] = Field(default_factory=list, description="Evidence snippets extracted from resume for requirement matching")
