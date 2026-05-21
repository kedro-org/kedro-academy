"""Apply approved proposal nodes."""

from __future__ import annotations

import hashlib
from typing import Any

from kedro_reflection_agent.utils.eval_dataset_format import from_langfuse_items, to_langfuse_items
from kedro_reflection_agent.data_models import EvalCase
from kedro_reflection_agent.pipelines.apply.models import AppliedMarker, utc_now_iso


def apply_prompt_and_skill(
    proposal_new_prompt: dict[str, Any],
    proposal_new_skill: str,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    _validate_prompt_skill(proposal_new_prompt, proposal_new_skill)
    return proposal_new_prompt["prompt"], proposal_new_prompt, proposal_new_skill, proposal_new_prompt


def merge_eval_dataset(
    eval_cases_file: list[dict[str, Any]],
    proposal_new_eval_cases: list[dict[str, Any]],
    proposal_bundle: dict[str, Any],
    proposal_new_skill: str,
    parameters: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    for raw in proposal_new_eval_cases:
        EvalCase.model_validate(raw)
    existing_cases = from_langfuse_items(eval_cases_file)
    merged_cases = _append_eval_cases(existing_cases, proposal_new_eval_cases)
    merged_langfuse = to_langfuse_items(merged_cases)
    proposal_id = parameters.get("proposal_id", proposal_bundle.get("proposal_id", "proposal_1"))
    marker = AppliedMarker(
        proposal_id=proposal_id,
        applied_at=utc_now_iso(),
        prompt_version="v2",
        skill_hash=hashlib.sha256(proposal_new_skill.encode()).hexdigest()[:12],
        new_eval_case_ids=[c["case_id"] for c in proposal_new_eval_cases],
    )
    return merged_langfuse, marker.model_dump()


def _validate_prompt_skill(proposal_new_prompt: dict[str, Any], proposal_new_skill: str) -> None:
    prompt_text = proposal_new_prompt.get("prompt", "")
    if not prompt_text.strip():
        raise ValueError("Proposed prompt is empty.")
    if not any(term.lower() in prompt_text.lower() for term in ("customer", "cta", "call to action")):
        raise ValueError("Proposed prompt missing required personalization/CTA guidance.")
    skill_lower = proposal_new_skill.lower()
    if not all(section in skill_lower for section in ("personalization", "cta", "guardrail")):
        raise ValueError("Proposed skill file missing required sections.")


def _append_eval_cases(
    eval_cases: list[dict[str, Any]],
    proposal_new_eval_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {c["case_id"] for c in eval_cases}
    merged = list(eval_cases)
    for raw in proposal_new_eval_cases:
        case = EvalCase.model_validate(raw)
        if case.case_id not in existing_ids:
            merged.append(case.model_dump())
    return merged
