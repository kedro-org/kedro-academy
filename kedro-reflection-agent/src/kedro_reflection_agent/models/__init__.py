"""Model registry.

Import from subpackages for explicit, agent-aware imports:
    from kedro_reflection_agent.models.shared import Signal, CaseScore
    from kedro_reflection_agent.models.b2b_sales import JudgeScore
    from kedro_reflection_agent.models.consumer_mktg import JudgeScore
    from kedro_reflection_agent.models.customer_care import JudgeScore

All shared models are also re-exported from this top-level package:
    from kedro_reflection_agent.models import Signal, CaseScore, EmailOutput
"""

from .shared import (
    AggregateScore,
    CaseScore,
    Confidence,
    Email,
    EmailOutput,
    EvalCase,
    EvaluationRecord,
    ProposedEvalCase,
    ReflectionChange,
    ReflectionIssue,
    ReflectionOutput,
    ReflectionSummary,
    Rubric,
    RunMetadata,
    Signal,
)

__all__ = [
    "Confidence",
    "Signal",
    "EmailOutput",
    "Email",
    "RunMetadata",
    "Rubric",
    "EvalCase",
    "EvaluationRecord",
    "CaseScore",
    "AggregateScore",
    "ReflectionIssue",
    "ReflectionChange",
    "ReflectionSummary",
    "ProposedEvalCase",
    "ReflectionOutput",
]
