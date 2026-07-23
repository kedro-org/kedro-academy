"""Pydantic models for applications pipeline."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

class ParsedResume(BaseModel):
    """Parsed resume model containing extracted text and candidate ID."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(description="Candidate identifier from document properties")
    raw_resume_text: str = Field(description="Extracted raw resume text")

class WorkHistory(BaseModel):
    """Work history entry."""

    model_config = ConfigDict(extra="forbid")

    company: str
    role: str
    duration: str
    description: str

class Education(BaseModel):
    """Education entry."""

    model_config = ConfigDict(extra="forbid")

    institution: str
    degree: str
    field: str | None = None
    year: str | None = None

class CandidateProfile(BaseModel):
    """Candidate profile model."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(description="Unique candidate identifier")
    name: str = Field(description="Candidate name")
    email: str = Field(description="Candidate email")
    skills: list[str] = Field(default_factory=list, description="List of skills")
    work_history: list[WorkHistory] = Field(default_factory=list, description="Work history")
    education: list[Education] = Field(default_factory=list, description="Education background")
    raw_resume_text: str = Field(description="Raw resume text")

class EvidenceSnippetMetadata(BaseModel):
    """Structured metadata for an evidence snippet."""

    model_config = ConfigDict(extra="forbid")

    section: str = Field(
        default="",
        description="Resume section the snippet came from, e.g. work_history or skills",
    )
    detail: str = Field(
        default="",
        description="Optional extra context about the snippet origin",
    )

class EvidenceSnippet(BaseModel):
    """Evidence snippet for matching."""

    model_config = ConfigDict(extra="forbid")

    snippet_id: str = Field(description="Unique snippet identifier")
    text: str = Field(description="Snippet text")
    source: str = Field(description="Source field (e.g., 'work_history', 'skills')")
    metadata: EvidenceSnippetMetadata = Field(
        default_factory=EvidenceSnippetMetadata,
        description="Additional metadata about snippet origin",
    )

class ResumeParsingOutput(BaseModel):
    """Expected output from resume parsing crew execution."""

    model_config = ConfigDict(extra="forbid")

    candidate_profile: CandidateProfile = Field(description="Extracted candidate profile")
    evidence_snippets: list[EvidenceSnippet] = Field(description="Evidence snippets for matching")

class Application(BaseModel):
    """Application model linking candidate to job.
    
    This model represents a candidate's application for a specific job position.
    It combines candidate information with job metadata and evidence snippets
    for use in the screening pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    application_id: str = Field(description="Unique application identifier (format: candidate_id_job_id)")
    candidate_id: str = Field(description="Candidate identifier")
    candidate_name: str = Field(description="Candidate name")
    submitted_at: datetime = Field(description="Submission timestamp")
    status: str = Field(default="pending", description="Application status")
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Job-related artifacts containing job_id, job_title, and location",
    )
    evidence_snippets: list[EvidenceSnippet] = Field(
        default_factory=list,
        description="Evidence snippets extracted from resume for requirement matching",
    )
