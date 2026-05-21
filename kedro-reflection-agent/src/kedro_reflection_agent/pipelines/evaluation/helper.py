"""Heuristic and aggregate scoring."""

from __future__ import annotations

import re
from collections import Counter

from kedro_reflection_agent.data_models import (
    AggregateScore,
    CaseScore,
    EmailOutput,
    EvalCase,
    GroundTruth,
    HeuristicScores,
    JudgeScore,
    ProductProfile,
)

CTA_KEYWORDS = ("book", "schedule", "review", "workshop", "call", "meeting", "discuss")
FAKE_SKU_PATTERNS = (r"SKU-", r"PROD-", r"\b50%\b", r"\bguaranteed\b")

DIMENSION_WEIGHTS = {
    "subject_relevance": 0.10,
    "length": 0.10,
    "cta": 0.15,
    "groundedness": 0.20,
    "personalization": 0.25,
    "writing_quality": 0.20,
}


def score_subject_present(subject: str) -> float:
    return 1.0 if subject.strip() else 0.0


def score_subject_length_ok(subject: str) -> float:
    length = len(subject.strip())
    return 1.0 if 35 <= length <= 90 else 0.0


def score_body_length_ok(body: str) -> float:
    words = len(body.split())
    return 1.0 if 90 <= words <= 170 else 0.0


def score_cta_present(body: str) -> float:
    lower = body.lower()
    return 1.0 if any(k in lower for k in CTA_KEYWORDS) else 0.0


def score_no_banned_claims(body: str, product: ProductProfile) -> float:
    lower = body.lower()
    for claim in product.avoid_claims:
        if claim.lower() in lower:
            return 0.0
    return 1.0


def score_no_fake_skus(body: str, product: ProductProfile) -> float:
    for pattern in FAKE_SKU_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            allowed = any(p.lower() in body.lower() for p in product.avoid_claims)
            if not allowed:
                return 0.0
    return 1.0


def score_must_mention_coverage(body: str, ground_truth: GroundTruth) -> float:
    if not ground_truth.must_mention:
        return 1.0
    lower = body.lower()
    hits = sum(1 for term in ground_truth.must_mention if term.lower() in lower)
    return hits / len(ground_truth.must_mention)


def score_must_not_mention_clean(body: str, ground_truth: GroundTruth) -> float:
    lower = body.lower()
    for term in ground_truth.must_not_mention:
        if term.lower() in lower:
            return 0.0
    return 1.0


def run_heuristics(
    email: EmailOutput,
    eval_case: EvalCase,
    product: ProductProfile,
) -> HeuristicScores:
    return HeuristicScores(
        subject_present=score_subject_present(email.subject),
        subject_length_ok=score_subject_length_ok(email.subject),
        body_length_ok=score_body_length_ok(email.body),
        cta_present=score_cta_present(email.body),
        no_banned_claims=score_no_banned_claims(email.body, product),
        no_fake_skus=score_no_fake_skus(email.body, product),
        must_mention_coverage=score_must_mention_coverage(email.body, eval_case.ground_truth),
        must_not_mention_clean=score_must_not_mention_clean(email.body, eval_case.ground_truth),
    )


def combine_case_score(heuristics: HeuristicScores, judge: JudgeScore) -> tuple[float, dict[str, float]]:
    subject_relevance = (heuristics.subject_present + judge.writing_quality / 10) / 2 * 10
    length_score = (heuristics.subject_length_ok + heuristics.body_length_ok) / 2 * 10
    cta_score = (heuristics.cta_present * 10 + judge.cta_quality) / 2
    groundedness = (heuristics.no_banned_claims * 10 + heuristics.no_fake_skus * 10 + judge.groundedness) / 3
    personalization = judge.personalization
    writing_quality = judge.writing_quality

    dimensions = {
        "subject_relevance": round(subject_relevance, 2),
        "length": round(length_score, 2),
        "cta": round(cta_score, 2),
        "groundedness": round(groundedness, 2),
        "personalization": round(personalization, 2),
        "writing_quality": round(writing_quality, 2),
        "heuristics": round(heuristics.average, 2),
    }
    total = sum(dimensions[k] * DIMENSION_WEIGHTS[k] for k in DIMENSION_WEIGHTS)
    return round(total, 2), dimensions


def aggregate_case_scores(run_id: str, case_scores: list[CaseScore]) -> AggregateScore:
    if not case_scores:
        return AggregateScore(
            run_id=run_id,
            aggregate_score=0.0,
            dimension_scores={},
            failure_tag_counts={},
            case_count=0,
        )
    dim_keys = ["writing_quality", "personalization", "groundedness", "cta", "heuristics", "length"]
    dimension_scores: dict[str, float] = {}
    for key in dim_keys:
        values = [cs.dimension_scores.get(key, 0) for cs in case_scores]
        dimension_scores[key] = round(sum(values) / len(values), 2)

    tag_counter: Counter[str] = Counter()
    for cs in case_scores:
        tag_counter.update(cs.failure_tags)

    aggregate = sum(cs.total_score for cs in case_scores) / len(case_scores)
    return AggregateScore(
        run_id=run_id,
        aggregate_score=round(aggregate, 2),
        dimension_scores=dimension_scores,
        failure_tag_counts=dict(tag_counter),
        case_count=len(case_scores),
    )
