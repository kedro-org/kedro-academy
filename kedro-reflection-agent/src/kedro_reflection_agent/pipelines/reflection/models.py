"""Reflection pipeline models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from kedro_reflection_agent.data_models import EvalCase


class ReflectionIssue(BaseModel):
    issue: str
    evidence: str
    example_case_ids: list[str] = Field(default_factory=list)


class ReflectionChange(BaseModel):
    change: str
    target: str


class ReflectionReason(BaseModel):
    reason: str


class ReflectionSummary(BaseModel):
    identified: list[ReflectionIssue] = Field(default_factory=list)
    fixed: list[ReflectionChange] = Field(default_factory=list)
    reasons: list[ReflectionReason] = Field(default_factory=list)


class ReflectionProposal(BaseModel):
    proposal_id: str
    run_id: str
    summary: ReflectionSummary
    new_system_prompt: str
    new_skill_file: str
    new_eval_cases: list[EvalCase] = Field(default_factory=list)
    expected_improvements: dict[str, float] = Field(default_factory=dict)
