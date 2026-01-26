"""Pydantic models for jobs pipeline."""

from pydantic import BaseModel, Field


class Requirements(BaseModel):
    """Job requirements structure."""

    must_have: list[str] = Field(default_factory=list, description="Must-have requirements")
    nice_to_have: list[str] = Field(default_factory=list, description="Nice-to-have requirements")


class JobPosting(BaseModel):
    """Job posting model."""

    job_id: str = Field(description="Unique job identifier")
    title: str = Field(description="Job title")
    location: str = Field(description="Job location")
    requirements: Requirements = Field(description="Job requirements")
    raw_jd_text: str = Field(description="Raw job description text")
