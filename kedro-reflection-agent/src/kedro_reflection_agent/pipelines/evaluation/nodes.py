"""Evaluation pipeline nodes."""

from __future__ import annotations

import json
import logging
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from kedro_reflection_agent.utils.eval_dataset_format import from_langfuse_items
from kedro_reflection_agent.base.llm import invoke_json
from kedro_reflection_agent.data_models import (
    CaseScore,
    CustomerProfile,
    EmailOutput,
    EvalCase,
    JudgeScore,
    ProductProfile,
)

from kedro_reflection_agent.pipelines.evaluation.helper import aggregate_case_scores, combine_case_score, run_heuristics

logger = logging.getLogger(__name__)


def _score_trace(client: Any, *, trace_id: str | None, name: str, value: float, comment: str | None = None) -> None:
    if client is None or not trace_id:
        return
    try:
        client.create_score(trace_id=trace_id, name=name, value=value, comment=comment or "")
        client.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Langfuse score write failed: %s", exc)


def _index(records: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {r[key]: r for r in records}


def evaluate_run(
    run_emails: list[dict[str, Any]],
    eval_cases_file: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    langfuse_tracer: Any,
    judge_llm_context: LLMContext,
    parameters: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    eval_cases = from_langfuse_items(eval_cases_file)
    run_id = parameters.get("run_id", "run_1")

    case_map = _index(eval_cases, "case_id")
    cust_map = _index(customers, "customer_id")
    prod_map = _index(products, "product_id")
    lf = langfuse_tracer

    case_scores: list[CaseScore] = []

    for raw_email in run_emails:
        email = EmailOutput.model_validate(raw_email)
        case = EvalCase.model_validate(case_map[email.case_id])
        customer = CustomerProfile.model_validate(cust_map[case.customer_id])
        product = ProductProfile.model_validate(prod_map[case.product_id])

        heuristics = run_heuristics(email, case, product)

        user = json.dumps(
            {
                "customer": customer.model_dump(),
                "product": product.model_dump(),
                "ground_truth": case.ground_truth.model_dump(),
                "subject": email.subject,
                "body": email.body,
            },
            indent=2,
        )
        judge = invoke_json(
            judge_llm_context,
            user,
            JudgeScore,
            system_key="judge_system_prompt",
        )

        total, dimensions = combine_case_score(heuristics, judge)
        failure_tags = list(set(judge.failure_tags))
        if total < 6:
            extras = [
                t
                for t in ("generic", "weak_cta", "missing_personalization", "not_grounded")
                if t not in failure_tags
            ][:3]
            failure_tags.extend(extras)

        cs = CaseScore(
            case_id=case.case_id,
            customer_id=customer.customer_id,
            product_id=product.product_id,
            company_name=customer.company_name,
            product_name=product.name,
            total_score=total,
            heuristic_scores=heuristics,
            judge_scores=judge,
            failure_tags=failure_tags if total < 7 else [],
            dimension_scores=dimensions,
        )
        case_scores.append(cs)

        _score_trace(
            lf,
            trace_id=email.metadata.trace_id,
            name="case_total",
            value=total,
            comment=judge.rationale,
        )

    aggregate = aggregate_case_scores(run_id, case_scores)
    return [cs.model_dump() for cs in case_scores], aggregate.model_dump()
