"""Pydantic models for jobs pipeline."""

from pydantic import BaseModel, Field


class Requirements(BaseModel):
    """Job requirements structure."""

    must_have: list[str] = Field(default_factory=list, description="Must-have requirements")
    nice_to_have: list[str] = Field(default_factory=list, description="Nice-to-have requirements")


class JobMetadata(BaseModel):
    """Job metadata model for applications pipeline."""

    job_id: str = Field(description="Unique job identifier")
    title: str = Field(description="Job title")
    location: str = Field(description="Job location")


class JobRequirements(BaseModel):
    """Job requirements model for screening pipeline."""

    job_id: str = Field(description="Unique job identifier")
    requirements: Requirements = Field(description="Job requirements")
