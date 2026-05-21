"""Pydantic models shared across pipelines.

Added incrementally as each pipeline iteration needs them.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# --- seed data ----------------------------------------------------------------


class Customer(BaseModel):
    customer_id: str
    company_name: str
    industry: Literal[
        "retail", "logistics", "banking", "manufacturing",
        "healthcare", "media", "utilities",
    ]
    company_size: Literal["small", "mid", "enterprise"]
    employee_count: int
    current_products: list[str]
    account_tenure_years: float
    primary_contact_name: str
    primary_contact_role: str
    region: str


class Product(BaseModel):
    product_id: str
    name: str
    short_description: str
    target_segment: Literal["small", "mid", "enterprise", "any"]
    key_benefits: list[str]
    pricing_tier: Literal["basic", "standard", "premium"]


# --- eval cases ---------------------------------------------------------------


class Rubric(BaseModel):
    required_mentions: list[str]
    forbidden_mentions: list[str]
    expected_cta: Literal["meeting", "demo", "call", "reply", "trial"]
    expected_tone: Literal["formal", "consultative", "friendly"]
    notes: str


class EvalCase(BaseModel):
    """Resolved view of one item in the Langfuse evaluation dataset."""

    case_id: str
    customer_id: str
    product_id: str
    rubric: Rubric


# --- campaign outputs --------------------------------------------------------


class EmailOutput(BaseModel):
    """Structured response schema enforced on the LLM in `campaign`."""

    subject: str = Field(..., description="The email's subject line.")
    body: str = Field(..., description="The email's body, plain text.")


class Email(BaseModel):
    """Full email envelope with execution metadata, persisted per case."""

    case_id: str
    customer_id: str
    product_id: str
    subject: str
    body: str
    trace_id: Optional[str] = None
    prompt_version: Optional[int] = None
    skill_version: Optional[str] = None
    model_name: str
    run_id: str
    generated_at: str


class RunMetadata(BaseModel):
    """Per-run summary persisted alongside the partitioned emails."""

    run_id: str
    n_cases: int
    n_emails: int
    n_errors: int
    model_name: str
    prompt_version: Optional[int] = None
    skill_version: Optional[str] = None
    started_at: str
    finished_at: str


# --- evaluation outputs ------------------------------------------------------


class JudgeScore(BaseModel):
    """Structured LLM-judge output for one email.

    All three dimensions are scored in a single LLM call so the judge reasons
    about them holistically and we keep cost/latency to one call per email.
    The combined judge evaluator returns this as three Langfuse ``Evaluation``s.
    """

    writing_quality: float = Field(..., ge=0.0, le=1.0)
    writing_quality_reason: str
    personalization: float = Field(..., ge=0.0, le=1.0)
    personalization_reason: str
    groundedness: float = Field(..., ge=0.0, le=1.0)
    groundedness_reason: str


class EvaluationRecord(BaseModel):
    """Disk-friendly serialisation of a single Langfuse ``Evaluation``."""

    name: str
    value: float
    comment: Optional[str] = None
    metadata: Optional[dict] = None


class CaseScore(BaseModel):
    """One row of ``per_case_scores.json``.

    Mirrors a single ``ExperimentItemResult`` from the Langfuse experiment
    plus our derived per-case mean and pass/fail.
    """

    case_id: str
    trace_id: Optional[str] = None
    dataset_run_id: Optional[str] = None
    output: dict  # the task's task output: {case_id, subject, body, [error]}
    evaluations: list[EvaluationRecord]
    mean_score: float = Field(..., ge=0.0, le=1.0)
    passing: bool


class AggregateScore(BaseModel):
    """Contents of ``aggregate_scores.json`` — run-level summary."""

    run_id: str
    experiment_name: str
    dataset_run_url: Optional[str] = None
    dataset_run_id: Optional[str] = None
    n_cases: int
    n_passing: int
    pass_rate: float = Field(..., ge=0.0, le=1.0)
    mean_total: float = Field(..., ge=0.0, le=1.0)
    mean_per_scorer: dict[str, float]
    passing_threshold: float
    model_name: str
    system_prompt_version: Optional[int] = None
    judge_model_name: str
    judge_prompt_version: Optional[int] = None
    started_at: str
    finished_at: str
