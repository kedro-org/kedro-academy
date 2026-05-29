"""Nodes for the ``evaluation`` pipeline.

Drives a Langfuse ``DatasetClient.run_experiment(...)`` over the evaluation
dataset. The task is an in-memory lookup of campaign-generated emails for the
given ``run_id`` (no LLM call inside the task); evaluators are 4 deterministic
heuristics + 1 combined LLM judge that returns 3 ``Evaluation`` objects per
case.

Topology (see ``pipeline.py``):
    judge_context_node              -> judge_context  (LLMContext)
    init_heuristic_evaluators(...)  -> heuristic_evaluators  (list[callable])
    init_judge_evaluator(...)       -> judge_evaluator  (callable)
    make_campaign_task(run_id)      -> campaign_task  (callable)
    run_experiment(...)             -> per_case_scores, aggregate_scores

This mirrors the ``intent_detection_evaluation`` pipeline in
``kedro-agentic-workflows`` (the source-of-truth project), adapted to our
"look up cached email" task shape and our multi-dimension combined judge.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

from kedro.pipeline import LLMContext
from langfuse import Evaluation
from langfuse._client.datasets import DatasetClient

from kedro_reflection_agent.models import b2b_sales as b2b_models
from kedro_reflection_agent.models import consumer_mktg as consumer_mktg_models
from kedro_reflection_agent.models import customer_care as customer_care_models
from kedro_reflection_agent.models.shared import AggregateScore, CaseScore, EvaluationRecord

_JUDGE_SCORE_BY_AGENT: dict[str, type] = {
    "b2b_sales": b2b_models.JudgeScore,
    "consumer_mktg": consumer_mktg_models.JudgeScore,
    "customer_care": customer_care_models.JudgeScore,
}
from kedro_reflection_agent.pipelines._common import build_structured_chain, utc_now_iso

logger = logging.getLogger(__name__)


# Scorer name groups, used for aggregation.
_HEURISTIC_NAMES = (
    "subject_present",
    "length_in_range",
    "no_fake_skus",
    "cta_present",
)
def _judge_names(judge_score_cls: type) -> tuple[str, ...]:
    """Derive scorer names from a JudgeScore model — excludes *_reason fields."""
    return tuple(f for f in judge_score_cls.model_fields if not f.endswith("_reason"))


# Regex patterns used by the heuristic evaluators below.
_SKU_PATTERN = re.compile(r"\b[A-Z]{2,}-?\d+\b")
_CTA_PATTERN = re.compile(
    r"\b(meeting|demo|call|reply|schedule|book(?:ing)?\s+a?\s*time|let'?s\s+(?:talk|chat|connect))\b",
    re.IGNORECASE,
)


# --- task ---------------------------------------------------------------------


def make_campaign_task(run_id: str, agent_id: str) -> Callable[..., dict[str, Any]]:
    """Build the experiment task: load the campaign-generated email by case_id.

    The Langfuse experiment iterates ``eval_cases``; for each item it calls this
    task. We look up the email that the ``campaign`` pipeline wrote at
    ``data/<agent_id>/outputs/runs/<run_id>/emails/<case_id>.json``.

    Returns a dict that downstream evaluators consume via the ``output`` kwarg.
    """
    emails_dir = Path("data") / agent_id / "outputs" / "runs" / run_id / "emails"

    def campaign_task(*, item, **kwargs) -> dict[str, Any]:
        case_id = item.input.get("case_id") or getattr(item, "id", None)
        path = emails_dir / f"{case_id}.json"
        if not path.exists():
            return {
                "case_id": case_id,
                "subject": "",
                "body": "",
                "error": f"email file not found: {path}",
            }
        email = json.loads(path.read_text())
        return {
            "case_id": case_id,
            "subject": email.get("subject", ""),
            "body": email.get("body", ""),
            "prompt_version": email.get("prompt_version"),
            "skill_version": email.get("skill_version"),
            "trace_id": email.get("trace_id"),
        }

    return campaign_task


# --- heuristic evaluators ----------------------------------------------------


def init_heuristic_evaluators(
    products: list[dict],
    body_length_min: int,
    body_length_max: int,
) -> list[Callable[..., Evaluation]]:
    """Return four pure-function evaluators (one per heuristic dimension)."""
    known_product_names = {p["name"].lower() for p in products}
    known_product_tokens = {
        tok.lower() for p in products for tok in p["name"].split()
    }

    def subject_present_evaluator(
        *, input, output, expected_output, **kwargs
    ) -> Evaluation:
        if output.get("error"):
            return Evaluation(
                name="subject_present",
                value=0.0,
                comment=f"task error: {output['error']}",
            )
        subject = (output.get("subject") or "").strip()
        return Evaluation(
            name="subject_present",
            value=1.0 if subject else 0.0,
            comment="Subject is non-empty." if subject else "Subject is empty.",
        )

    def length_in_range_evaluator(
        *, input, output, expected_output, **kwargs
    ) -> Evaluation:
        if output.get("error"):
            return Evaluation(
                name="length_in_range",
                value=0.0,
                comment=f"task error: {output['error']}",
            )
        body = output.get("body") or ""
        n = len(body)
        ok = body_length_min <= n <= body_length_max
        return Evaluation(
            name="length_in_range",
            value=1.0 if ok else 0.0,
            comment=(
                f"Body is {n} chars (within [{body_length_min}, {body_length_max}])."
                if ok
                else f"Body is {n} chars (outside [{body_length_min}, {body_length_max}])."
            ),
        )

    def no_fake_skus_evaluator(
        *, input, output, expected_output, **kwargs
    ) -> Evaluation:
        if output.get("error"):
            return Evaluation(
                name="no_fake_skus",
                value=0.0,
                comment=f"task error: {output['error']}",
            )
        body = output.get("body") or ""
        suspects: list[str] = []
        for match in _SKU_PATTERN.findall(body):
            m_lower = match.lower()
            if m_lower in known_product_names:
                continue
            if any(m_lower in name for name in known_product_names):
                continue
            if m_lower in known_product_tokens:
                continue
            suspects.append(match)
        if not suspects:
            return Evaluation(
                name="no_fake_skus",
                value=1.0,
                comment="No SKU-shaped tokens outside known product names.",
            )
        return Evaluation(
            name="no_fake_skus",
            value=0.0,
            comment=f"Potentially fabricated SKU tokens: {', '.join(suspects[:5])}.",
        )

    def cta_present_evaluator(
        *, input, output, expected_output, **kwargs
    ) -> Evaluation:
        if output.get("error"):
            return Evaluation(
                name="cta_present",
                value=0.0,
                comment=f"task error: {output['error']}",
            )
        body = output.get("body") or ""
        rubric = (expected_output or {}).get("rubric", {})
        expected_cta = rubric.get("expected_cta", "unspecified")
        if _CTA_PATTERN.search(body):
            return Evaluation(
                name="cta_present",
                value=1.0,
                comment="Body contains a recognisable call-to-action.",
            )
        return Evaluation(
            name="cta_present",
            value=0.0,
            comment=(
                f"No CTA matching meeting/demo/call/reply "
                f"(rubric expected: {expected_cta})."
            ),
        )

    return [
        subject_present_evaluator,
        length_in_range_evaluator,
        no_fake_skus_evaluator,
        cta_present_evaluator,
    ]


# --- judge evaluator ---------------------------------------------------------


def init_judge_evaluator(
    judge_context: LLMContext,
    customers: list[dict],
    products: list[dict],
    agent_id: str,
) -> Callable[..., list[Evaluation]]:
    """Return a combined evaluator that does one LLM call per output and emits
    one ``Evaluation`` per judge dimension (derived from the agent's JudgeScore)."""
    judge_score_cls = _JUDGE_SCORE_BY_AGENT[agent_id]
    names = _judge_names(judge_score_cls)
    chain = build_structured_chain(judge_context, "judge_prompt", judge_score_cls)
    customer_by_id = {c["customer_id"]: c for c in customers}
    product_by_id = {p["product_id"]: p for p in products}

    def judge_evaluator(
        *, input, output, expected_output, **kwargs
    ) -> list[Evaluation]:
        if output.get("error"):
            return [
                Evaluation(name=name, value=0.0, comment=f"task error: {output['error']}")
                for name in names
            ]

        customer = customer_by_id.get((input or {}).get("customer_id"))
        product = product_by_id.get((input or {}).get("product_id"))
        rubric = (expected_output or {}).get("rubric", {})

        payload = {
            "customer": json.dumps(customer, indent=2) if customer else "(unknown)",
            "product": json.dumps(product, indent=2) if product else "(unknown)",
            "rubric": json.dumps(rubric, indent=2),
            "subject": output.get("subject", ""),
            "body": output.get("body", ""),
        }

        try:
            result = chain.invoke(payload)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Judge LLM call failed: %s", exc)
            return [
                Evaluation(name=name, value=0.0, comment=f"judge error: {exc}")
                for name in names
            ]

        return [
            Evaluation(
                name=name,
                value=float(getattr(result, name)),
                comment=getattr(result, f"{name}_reason", ""),
            )
            for name in names
        ]

    return judge_evaluator


# --- experiment driver -------------------------------------------------------


def run_experiment(
    eval_cases: DatasetClient,
    campaign_task: Callable[..., dict[str, Any]],
    heuristic_evaluators: list[Callable[..., Evaluation]],
    judge_evaluator: Callable[..., list[Evaluation]],
    run_id: str,
    agent_id: str,
    model_name: str,
    system_prompt_version: int,
    judge_model_name: str,
    judge_prompt_version: int,
    passing_threshold: float,
) -> tuple[list[dict], dict]:
    """Run the Langfuse experiment and produce disk-side score artifacts.

    The experiment is stored in Langfuse as a dataset run named after the
    ``run_id`` + the campaign prompt version, so successive experiments (e.g.
    before and after reflection) are easy to compare in the Langfuse UI.
    """
    started_at = utc_now_iso()
    experiment_name = (
        f"campaign_{run_id}_prompt_v{system_prompt_version}"
    )

    result = eval_cases.run_experiment(
        name=experiment_name,
        task=campaign_task,
        evaluators=[*heuristic_evaluators, judge_evaluator],
        metadata={
            "run_id": run_id,
            "model_name": model_name,
            # OpenTelemetry baggage requires strings; int versions get coerced.
            "system_prompt_version": str(system_prompt_version),
            "judge_model_name": judge_model_name,
            "judge_prompt_version": str(judge_prompt_version),
            "passing_threshold": str(passing_threshold),
        },
    )

    all_scorer_names = _HEURISTIC_NAMES + _judge_names(_JUDGE_SCORE_BY_AGENT[agent_id])

    per_case: list[CaseScore] = []
    per_scorer_values: dict[str, list[float]] = {n: [] for n in all_scorer_names}

    for item_result in result.item_results:
        case_id = getattr(item_result.item, "id", None) or (
            item_result.item.get("id") if isinstance(item_result.item, dict) else None
        )
        evals = [
            EvaluationRecord(
                name=e.name,
                value=float(e.value),
                comment=e.comment,
                metadata=e.metadata,
            )
            for e in item_result.evaluations
        ]
        values_by_name = {e.name: e.value for e in evals}
        ordered_values = [
            values_by_name.get(name, 0.0) for name in all_scorer_names
        ]
        mean_score = (
            sum(ordered_values) / len(ordered_values) if ordered_values else 0.0
        )
        passing = mean_score >= passing_threshold

        for name, value in values_by_name.items():
            if name in per_scorer_values:
                per_scorer_values[name].append(float(value))

        per_case.append(
            CaseScore(
                case_id=case_id or "(unknown)",
                trace_id=item_result.trace_id,
                dataset_run_id=item_result.dataset_run_id,
                output=item_result.output if isinstance(item_result.output, dict) else {"value": item_result.output},
                evaluations=evals,
                mean_score=mean_score,
                passing=passing,
            )
        )

    n_cases = len(per_case)
    n_passing = sum(1 for cs in per_case if cs.passing)
    mean_total = (
        sum(cs.mean_score for cs in per_case) / n_cases if n_cases else 0.0
    )
    mean_per_scorer = {
        name: (sum(vs) / len(vs)) if vs else 0.0
        for name, vs in per_scorer_values.items()
    }

    aggregate = AggregateScore(
        run_id=run_id,
        experiment_name=experiment_name,
        dataset_run_url=getattr(result, "dataset_run_url", None),
        dataset_run_id=getattr(result, "dataset_run_id", None),
        n_cases=n_cases,
        n_passing=n_passing,
        pass_rate=n_passing / n_cases if n_cases else 0.0,
        mean_total=mean_total,
        mean_per_scorer=mean_per_scorer,
        passing_threshold=passing_threshold,
        model_name=model_name,
        system_prompt_version=system_prompt_version,
        judge_model_name=judge_model_name,
        judge_prompt_version=judge_prompt_version,
        started_at=started_at,
        finished_at=utc_now_iso(),
    )

    logger.info(
        "evaluation %s: %d/%d passing (%.0f%%), mean_total=%.2f, dashboard=%s",
        run_id,
        n_passing,
        n_cases,
        100 * aggregate.pass_rate,
        mean_total,
        aggregate.dataset_run_url or "(no url)",
    )

    return [cs.model_dump() for cs in per_case], aggregate.model_dump()
