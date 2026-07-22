"""Pydantic models for reporting pipeline."""

from pydantic import BaseModel, Field


class EmailDraft(BaseModel):
    """Email draft model."""

    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")
    placeholders: dict[str, str] = Field(default_factory=dict, description="Template placeholders")
