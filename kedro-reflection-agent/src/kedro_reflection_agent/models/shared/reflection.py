"""Reflection models shared across all agents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .evaluation import EvalCase


class ReflectionIssue(BaseModel):
    issue: str
    evidence: str
    example_case_ids: list[str] = Field(default_factory=list)


class ReflectionChange(BaseModel):
    change: str
    target: str  # "system_prompt" | "skill_file" | "eval_dataset"


class ReflectionSummary(BaseModel):
    identified: list[ReflectionIssue]
    fixed: list[ReflectionChange]
    reasons: list[str]


class ProposedEvalCase(EvalCase):
    """New eval case proposed by the reflection pipeline."""

    reason_added: str = ""


class ReflectionOutput(BaseModel):
    """Structured output from the meta-agent LLM call."""

    summary: ReflectionSummary
    new_prompt_text: str = Field(
        ...,
        description=(
            "Complete improved system prompt text. "
            "Must retain the {skill} placeholder where the skill file is injected."
        ),
    )
    new_skill_text: str = Field(
        ..., description="Complete improved skill file content in markdown."
    )
    new_eval_cases: list[ProposedEvalCase] = Field(
        default_factory=list,
        description="2-3 new regression eval cases derived from the identified failure modes.",
    )
