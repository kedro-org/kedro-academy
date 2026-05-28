"""Evaluation models shared across all agents."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Rubric(BaseModel):
    required_mentions: list[str]
    forbidden_mentions: list[str]
    expected_cta: Literal["meeting", "demo", "call", "reply", "trial"]
    expected_tone: Literal["formal", "consultative", "friendly"]
    notes: str


class EvalCase(BaseModel):
    """Resolved view of one item in a Langfuse evaluation dataset."""

    case_id: str
    customer_id: str
    product_id: str
    rubric: Rubric


class EvaluationRecord(BaseModel):
    """Disk-friendly serialisation of a single Langfuse Evaluation."""

    name: str
    value: float
    comment: Optional[str] = None
    metadata: Optional[dict] = None


class CaseScore(BaseModel):
    """One row of ``per_case_scores.json``."""

    case_id: str
    trace_id: Optional[str] = None
    dataset_run_id: Optional[str] = None
    output: dict
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
