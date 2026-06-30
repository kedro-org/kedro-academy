"""Campaign output models shared across all agents."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EmailOutput(BaseModel):
    """Structured LLM response schema enforced in the campaign node."""

    subject: str = Field(..., description="The message subject line.")
    body: str = Field(..., description="The message body, plain text.")


class Email(BaseModel):
    """Full output envelope with execution metadata, persisted per case."""

    case_id: str
    customer_id: str
    product_id: str
    subject: str
    body: str
    trace_id: Optional[str] = None
    prompt_version: int = 1
    model_name: str
    run_id: str
    generated_at: str


class RunMetadata(BaseModel):
    """Per-run summary persisted alongside the partitioned outputs."""

    run_id: str
    agent_id: str
    n_cases: int
    n_emails: int
    n_errors: int
    model_name: str
    prompt_version: int = 1
    started_at: str
    finished_at: str
