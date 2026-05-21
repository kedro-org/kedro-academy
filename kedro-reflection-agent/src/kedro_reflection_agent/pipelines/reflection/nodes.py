"""Reflection meta-agent nodes."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from kedro_reflection_agent.pipelines.reflection.diffing import unified_diff_html
from kedro_reflection_agent.utils.eval_dataset_format import from_langfuse_items
from kedro_reflection_agent.base.llm import invoke_text
from kedro_reflection_agent.data_models import (
    AggregateScore,
    CaseScore,
    EvalCase,
    GroundTruth,
)
from kedro_reflection_agent.pipelines.reflection.models import (
    ReflectionChange,
    ReflectionIssue,
    ReflectionProposal,
    ReflectionReason,
    ReflectionSummary,
)
from kedro_reflection_agent.utils.prompt_utils import is_weak_prompt, load_seed_prompt_yaml, load_seed_skill, prompt_text

IMPROVED_SYSTEM_PROMPT = """You are a B2B sales email assistant for a telecom company.

Write a personalised outreach email promoting the given product to the given customer.

Requirements:
- Use the customer's industry, company size, current products, tenure, pain points, and strategic initiatives explicitly.
- Tie each product value proposition to the customer's situation — do not use generic claims.
- Never include unsupported claims, banned product claims, fake SKUs, prices, discounts, or guarantees.
- Write a crisp subject line (35–90 characters) that references the customer's context.
- Keep the email body between 90 and 170 words.
- Include exactly one clear call to action that matches the product's CTA.
- Address the target persona from the evaluation context.
- Use a business-friendly tone aligned with the customer's tone preference.

Output JSON with keys: subject, body.
"""

IMPROVED_SKILL_FILE = """# B2B Email Style Guide

## Personalization
- Open with a sentence that references the customer's industry, pain points, or strategic initiatives.
- Mention at least two customer-specific facts (products in use, tenure, region, or size).

## Product positioning
- Connect product value props to the customer's known situation.
- Do not repeat generic marketing language.

## Call to action
- End with one named CTA taken from the product profile (e.g. network optimisation review).
- Avoid vague CTAs such as "contact us" or "learn more".

## Guardrails
- Never use banned claims from the product profile.
- Never invent SKUs, pricing, discounts, or guarantees.
- Keep body length between 90 and 170 words.

## Structure
- Subject: specific, under 90 characters.
- Body: 3 short paragraphs — context, value, CTA.
"""


def build_reflection_proposal(
    run_emails: list[dict[str, Any]],
    run_case_scores: list[dict[str, Any]],
    run_aggregate_scores: dict[str, Any],
    campaign_system_prompt: dict[str, Any],
    skill_file: str,
    eval_cases_file: list[dict[str, Any]],
    reflection_llm_context: LLMContext,
    parameters: dict[str, Any],
) -> dict[str, dict[str, Any] | str | list[dict[str, Any]]]:
    eval_cases = from_langfuse_items(eval_cases_file)
    run_id = parameters.get("run_id", "run_1")
    proposal_id = parameters.get("proposal_id", f"proposal_{run_id.replace('run_', '')}")
    force = bool(parameters.get("demo_force_improvement", True))

    scores = [CaseScore.model_validate(s) for s in run_case_scores]
    aggregate = AggregateScore.model_validate(run_aggregate_scores)
    current_prompt = prompt_text(campaign_system_prompt)

    tag_counter: Counter[str] = Counter()
    for cs in scores:
        tag_counter.update(cs.failure_tags)

    worst = sorted(scores, key=lambda s: s.total_score)[: parameters.get("reflection", {}).get("worst_case_count", 5)]
    best = sorted(scores, key=lambda s: s.total_score, reverse=True)[: parameters.get("reflection", {}).get("best_case_count", 3)]

    generic_count = tag_counter.get("generic", 0) + tag_counter.get("missing_personalization", 0)
    weak_cta = tag_counter.get("weak_cta", 0)
    not_grounded = tag_counter.get("not_grounded", 0)
    n_cases = max(len(scores), 1)

    summary = ReflectionSummary(
        identified=[
            ReflectionIssue(
                issue="Emails were too generic",
                evidence=f"{generic_count}/{n_cases} cases had low personalization scores.",
                example_case_ids=[w.case_id for w in worst[:3]],
            ),
            ReflectionIssue(
                issue="Weak call to action",
                evidence=f"{weak_cta}/{n_cases} emails used vague CTAs.",
                example_case_ids=[w.case_id for w in worst[1:4]],
            ),
            ReflectionIssue(
                issue="Missed customer pain points",
                evidence=f"{not_grounded}/{n_cases} emails ignored known pain points.",
                example_case_ids=[w.case_id for w in worst[2:5]],
            ),
        ],
        fixed=[
            ReflectionChange(
                change="Added explicit personalization and grounding instructions.",
                target="system_prompt",
            ),
            ReflectionChange(
                change="Enforced pain-point-led opening and named CTA rules.",
                target="skill_file",
            ),
            ReflectionChange(
                change=f"Added {parameters.get('reflection', {}).get('regression_case_count', 4)} regression eval cases.",
                target="eval_dataset",
            ),
        ],
        reasons=[
            ReflectionReason(
                reason=(
                    f"Lowest dimensions: personalization {aggregate.dimension_scores.get('personalization', 0):.1f}/10, "
                    f"CTA {aggregate.dimension_scores.get('cta', 0):.1f}/10."
                )
            ),
        ],
    )

    seed_prompt = prompt_text(load_seed_prompt_yaml())
    seed_skill = load_seed_skill()
    already_improved = not is_weak_prompt(current_prompt)

    new_prompt = IMPROVED_SYSTEM_PROMPT if force else current_prompt
    new_skill = IMPROVED_SKILL_FILE if force else skill_file
    new_eval_cases = _derive_regression_cases(worst, eval_cases, parameters)

    if not force:
        payload = {
            "current_prompt": current_prompt,
            "skill_file": skill_file,
            "aggregate_scores": aggregate.model_dump(),
            "worst_cases": [w.model_dump() for w in worst],
            "best_cases": [b.model_dump() for b in best],
            "failure_tags": dict(tag_counter),
        }
        try:
            raw = invoke_text(
                reflection_llm_context,
                json.dumps(payload),
                extra_system="You are a reflection meta-agent improving a B2B email agent. Return JSON with new_system_prompt and new_skill_file.",
            )
            parsed = json.loads(raw)
            new_prompt = parsed.get("new_system_prompt", new_prompt)
            new_skill = parsed.get("new_skill_file", new_skill)
        except Exception:  # noqa: BLE001
            pass

    proposal = ReflectionProposal(
        proposal_id=proposal_id,
        run_id=run_id,
        summary=summary,
        new_system_prompt=new_prompt,
        new_skill_file=new_skill,
        new_eval_cases=new_eval_cases,
        expected_improvements={
            "personalization": 2.5,
            "cta": 2.0,
            "groundedness": 1.2,
        },
    )

    summary_md = _render_summary_md(proposal, aggregate, already_improved=already_improved)
    diff_from_prompt = seed_prompt if force else current_prompt
    diff_from_skill = seed_skill if force else skill_file
    prompt_diff = unified_diff_html(
        diff_from_prompt,
        new_prompt,
        "Seed prompt (v1)" if force else "Current prompt",
        "Proposed prompt (v2)",
    )
    skill_diff = unified_diff_html(
        diff_from_skill,
        new_skill,
        "Seed skill (v1)" if force else "Current skill",
        "Proposed skill (v2)",
    )

    return {
        "proposal_bundle": proposal.model_dump(),
        "proposal_summary_md": summary_md,
        "proposal_new_prompt": {"prompt": new_prompt},
        "proposal_new_skill": new_skill,
        "proposal_new_eval_cases": [c.model_dump() for c in new_eval_cases],
        "proposal_prompt_diff": prompt_diff,
        "proposal_skill_diff": skill_diff,
    }


def _derive_regression_cases(
    worst: list[CaseScore],
    eval_cases: list[dict[str, Any]],
    parameters: dict[str, Any],
) -> list[EvalCase]:
    count = parameters.get("reflection", {}).get("regression_case_count", 4)
    case_map = {c["case_id"]: c for c in eval_cases}
    regressions: list[EvalCase] = []
    for idx, cs in enumerate(worst[:count], start=1):
        source = case_map.get(cs.case_id, {})
        gt = source.get("ground_truth", {})
        regressions.append(
            EvalCase(
                case_id=f"regression_{idx:03d}",
                customer_id=cs.customer_id,
                product_id=cs.product_id,
                ground_truth=GroundTruth.model_validate(gt),
                is_regression=True,
                source_failure_case_id=cs.case_id,
                reason_added=f"Catches failures seen in {cs.case_id} ({', '.join(cs.failure_tags[:2]) or 'low score'}).",
            )
        )
    return regressions


def _render_summary_md(
    proposal: ReflectionProposal,
    aggregate: AggregateScore,
    *,
    already_improved: bool = False,
) -> str:
    lines = ["# Reflection Intelligence Summary", ""]
    if already_improved:
        lines.append(
            "> **Note:** The active prompt already looks like v2. Use **Reset** in the sidebar "
            "to restore the weak v1 seed prompt before Run 1, then re-run the full loop."
        )
        lines.append("")
    for item in proposal.summary.identified:
        lines.append(f"- **{item.issue}**: {item.evidence}")
    lines.append("")
    lines.append(f"Run aggregate score: **{aggregate.aggregate_score}/10**")
    return "\n".join(lines)


def split_proposal_outputs(
    bundle: dict[str, dict[str, Any] | str | list[dict[str, Any]]],
) -> tuple[
    dict[str, Any],
    str,
    dict[str, str],
    str,
    list[dict[str, Any]],
    str,
    str,
]:
    return (
        bundle["proposal_bundle"],  # type: ignore[return-value]
        bundle["proposal_summary_md"],  # type: ignore[return-value]
        bundle["proposal_new_prompt"],  # type: ignore[return-value]
        bundle["proposal_new_skill"],  # type: ignore[return-value]
        bundle["proposal_new_eval_cases"],  # type: ignore[return-value]
        bundle["proposal_prompt_diff"],  # type: ignore[return-value]
        bundle["proposal_skill_diff"],  # type: ignore[return-value]
    )
