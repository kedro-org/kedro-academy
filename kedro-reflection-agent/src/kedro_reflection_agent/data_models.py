"""Pydantic models shared across pipelines."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CustomerProfile(BaseModel):
    customer_id: str
    company_name: str
    industry: str
    size: str
    employee_count: int
    locations: int
    region: str
    current_products: list[str]
    account_tenure_years: int
    known_pain_points: list[str]
    strategic_initiatives: list[str]
    tone_preference: str
    relationship_context: str


class ProductProfile(BaseModel):
    product_id: str
    name: str
    category: str
    ideal_for: list[str]
    value_props: list[str]
    avoid_claims: list[str]
    cta: str


class GroundTruth(BaseModel):
    must_mention: list[str]
    must_not_mention: list[str]
    desired_cta_type: str
    personalization_angle: str
    target_persona: str


class EvalCase(BaseModel):
    case_id: str
    customer_id: str
    product_id: str
    ground_truth: GroundTruth
    is_regression: bool = False
    source_failure_case_id: str | None = None
    reason_added: str | None = None


class EmailMetadata(BaseModel):
    prompt_version: str
    skill_version: str
    model: str
    run_id: str
    trace_id: str | None = None
    trace_url: str | None = None


class EmailOutput(BaseModel):
    case_id: str
    subject: str
    body: str
    metadata: EmailMetadata


class JudgeScore(BaseModel):
    writing_quality: float = Field(ge=0, le=10)
    personalization: float = Field(ge=0, le=10)
    groundedness: float = Field(ge=0, le=10)
    cta_quality: float = Field(ge=0, le=10)
    rationale: str = ""
    failure_tags: list[str] = Field(default_factory=list)


class HeuristicScores(BaseModel):
    subject_present: float
    subject_length_ok: float
    body_length_ok: float
    cta_present: float
    no_banned_claims: float
    no_fake_skus: float
    must_mention_coverage: float
    must_not_mention_clean: float

    @property
    def average(self) -> float:
        values = [
            self.subject_present,
            self.subject_length_ok,
            self.body_length_ok,
            self.cta_present,
            self.no_banned_claims,
            self.no_fake_skus,
            self.must_mention_coverage,
            self.must_not_mention_clean,
        ]
        return sum(values) / len(values) * 10


class CaseScore(BaseModel):
    case_id: str
    customer_id: str
    product_id: str
    company_name: str
    product_name: str
    total_score: float
    heuristic_scores: HeuristicScores
    judge_scores: JudgeScore
    failure_tags: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, float] = Field(default_factory=dict)


class AggregateScore(BaseModel):
    run_id: str
    aggregate_score: float
    dimension_scores: dict[str, float]
    failure_tag_counts: dict[str, int]
    case_count: int
