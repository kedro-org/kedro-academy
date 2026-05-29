"""Nodes for the ``reflection`` pipeline.

The meta-agent reads the current prompt + skill file + per-case scores (with
email content) + eval-case rubrics, then proposes:
  - a narrative summary  (identified / fixed / reasons)
  - an improved system prompt
  - an updated skill file
  - new eval cases derived from the identified failure modes

Topology (see ``pipeline.py``):
    meta_agent_context_node
        -> meta_agent_context  (LLMContext)
    prepare_reflection_context(system_prompt, skill_text, per_case_scores,
                               aggregate_scores, eval_cases, passing_threshold)
        -> reflection_context  (dict matching meta_agent_prompt template vars)
    reflect(meta_agent_context, reflection_context, run_id, reflection_id)
        -> reflection_summary, proposed_prompt, proposed_skill, proposed_eval_cases
"""

from __future__ import annotations

import json
import logging
from typing import Any

from kedro.pipeline import LLMContext

from ...models.shared import AggregateScore, CaseScore, ReflectionOutput, ReflectionSummary
from ...utils.id_service import dataset_item_id
from .._common import build_structured_chain, utc_now_iso

logger = logging.getLogger(__name__)

_N_WORST_CASES = 5

# Human-message template preserved verbatim from the current system_prompt.json.
# Only the system message changes across reflection cycles; the data-provision
# template (customer / product / skill injection) stays constant.
#
# Source of truth: data/campaign/prompts/system_prompt.json (human message),
# also embedded in scripts/seed_demo.py (SEED_SYSTEM_PROMPT).
# Keep all three in sync if the human message ever changes.
_HUMAN_TEMPLATE = (
    "Write an outreach email to this customer about this product.\n\n"
    "Customer:\n{customer}\n\nProduct:\n{product}"
)


def prepare_reflection_context(
    system_prompt: Any,
    skill_text: str,
    per_case_scores: list[dict],
    aggregate_scores: dict,
    eval_cases: Any,
    passing_threshold: float,
) -> dict[str, str]:
    """Build the context dict for the meta-agent chain.

    Keys match the template variables declared in meta_agent_prompt.json:
    ``current_prompt``, ``skill_text``, ``aggregate_scores_json``,
    ``failing_cases_json``.
    """
    current_prompt = _extract_prompt_text(system_prompt)

    rubric_by_case_id: dict[str, dict] = {}
    for item in eval_cases.items:
        rubric_by_case_id[item.id] = (item.expected_output or {}).get("rubric", {})

    scores = [CaseScore.model_validate(s) for s in per_case_scores]
    # Drop cases that errored in the Langfuse experiment (no local email was
    # generated for them — their output has no "body" field).
    scores = [s for s in scores if s.output.get("body", "").strip()]
    failing = [s for s in scores if not s.passing]

    if not failing:
        logger.warning(
            "reflection: no failing cases found (threshold=%.2f); "
            "using the %d lowest-scoring cases instead",
            passing_threshold,
            _N_WORST_CASES,
        )
        failing = sorted(scores, key=lambda s: s.mean_score)

    worst = sorted(failing, key=lambda s: s.mean_score)[:_N_WORST_CASES]

    failing_cases_payload = []
    for cs in worst:
        failing_cases_payload.append({
            "case_id": cs.case_id,
            "mean_score": round(cs.mean_score, 3),
            "email": {
                "subject": cs.output.get("subject", ""),
                "body": cs.output.get("body", ""),
            },
            "evaluations": [
                {
                    "name": e.name,
                    "value": round(e.value, 3),
                    "comment": e.comment,
                }
                for e in cs.evaluations
            ],
            "rubric": rubric_by_case_id.get(cs.case_id, {}),
        })

    logger.info(
        "reflection context: %d failing / %d total cases; showing %d worst to meta-agent",
        len(failing),
        len(scores),
        len(worst),
    )

    return {
        "current_prompt": current_prompt,
        "skill_text": skill_text,
        "aggregate_scores_json": json.dumps(aggregate_scores, indent=2),
        "failing_cases_json": json.dumps(failing_cases_payload, indent=2),
    }


def reflect(
    meta_agent_context: LLMContext,
    reflection_context: dict[str, str],
    run_id: str,
    reflection_id: str,
    agent_id: str,
) -> tuple[str, list[dict], str, list[dict]]:
    """Invoke the meta-agent and produce the four reflection artifacts.

    Returns:
        reflection_summary   – markdown narrative (summary.md)
        proposed_prompt      – list of chat messages (proposed_prompt.json)
        proposed_skill       – markdown skill file  (proposed_skill.md)
        proposed_eval_cases  – list of dicts        (proposed_eval_cases.json)
    """
    chain = build_structured_chain(meta_agent_context, "meta_agent_prompt", ReflectionOutput)

    logger.info(
        "reflection %s (run=%s): invoking meta-agent",
        reflection_id,
        run_id,
    )

    result: ReflectionOutput = chain.invoke(reflection_context)

    summary_md = _render_summary_md(result.summary, reflection_id, run_id)

    proposed_prompt = [
        {"role": "system", "content": result.new_prompt_text},
        {"role": "human", "content": _HUMAN_TEMPLATE},
    ]

    proposed_eval_cases = [
        {
            "id": dataset_item_id(agent_id, ec.case_id),
            "input": {
                "case_id": ec.case_id,
                "customer_id": ec.customer_id,
                "product_id": ec.product_id,
            },
            "expected_output": {"rubric": ec.rubric.model_dump()},
        }
        for ec in result.new_eval_cases
    ]

    logger.info(
        "reflection %s: %d issues identified, %d changes proposed, "
        "%d new eval cases",
        reflection_id,
        len(result.summary.identified),
        len(result.summary.fixed),
        len(proposed_eval_cases),
    )

    return summary_md, proposed_prompt, result.new_skill_text, proposed_eval_cases


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_prompt_text(prompt: Any) -> str:
    """Extract the system message template from a ChatPromptTemplate.

    Only the system message content is returned — that is what the meta-agent
    should improve and what ``new_prompt_text`` maps back to. The human
    template is fixed and is re-attached in ``reflect()`` separately.
    """
    for msg in prompt.messages:
        role = type(msg).__name__.replace("MessagePromptTemplate", "").lower()
        if "system" in role:
            inner = getattr(msg, "prompt", None)
            return getattr(inner, "template", None) or str(msg)
    # Fallback: join all messages if no system role found
    parts = []
    for msg in prompt.messages:
        role = type(msg).__name__.replace("MessagePromptTemplate", "").lower()
        inner = getattr(msg, "prompt", None)
        template_str = getattr(inner, "template", None) or str(msg)
        parts.append(f"[{role}]\n{template_str}")
    return "\n\n".join(parts)


def _render_summary_md(
    summary: ReflectionSummary,
    reflection_id: str,
    run_id: str,
) -> str:
    lines = [
        f"# Reflection {reflection_id} (run: {run_id})",
        f"_Generated at {utc_now_iso()}_",
        "",
        "## Issues identified",
        "",
    ]
    for issue in summary.identified:
        lines.append(f"### {issue.issue}")
        lines.append(f"{issue.evidence}")
        if issue.example_case_ids:
            lines.append(f"_Example cases: {', '.join(issue.example_case_ids)}_")
        lines.append("")

    lines += ["## Changes proposed", ""]
    for change in summary.fixed:
        lines.append(f"- **{change.target}**: {change.change}")
    lines.append("")

    lines += ["## Reasons", ""]
    for reason in summary.reasons:
        lines.append(f"- {reason}")

    return "\n".join(lines)
