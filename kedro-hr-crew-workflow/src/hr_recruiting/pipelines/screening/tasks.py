"""Task creation functions for screening pipeline.

This module contains factory functions for creating CrewAI tasks
used in the screening workflow.
"""

from typing import Any

from crewai import Agent, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.pipelines.screening.helper import extract_task_fields_from_prompt
from hr_recruiting.pipelines.screening.models import (
    RequirementsMatchingResult,
    ScreeningEvaluationOutput,
)


def create_requirements_matching_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create requirements matching task.

    Args:
        context: LLMContext containing prompts
        agent: Requirements matcher agent

    Returns:
        Configured Task instance
    """
    description, expected_output = extract_task_fields_from_prompt(
        context=context,
        prompt_name="requirements_matching_user_prompt",
        model_class=RequirementsMatchingResult,
        format_kwargs={
            "must_have_requirements": "",
            "evidence_snippets": "",
        },
    )

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
        output_pydantic=RequirementsMatchingResult,
    )


def create_resume_evaluation_task(
    context: LLMContext,
    agent: Agent,
    matching_result: dict[str, Any],
    scoring_result: dict[str, Any],
) -> Task:
    """Create resume evaluation task with pre-computed scores in the prompt.

    Args:
        context: LLMContext containing prompts
        agent: Resume evaluator agent
        matching_result: Output from requirements matching (match_results + metadata)
        scoring_result: Deterministic match_score and must_have_coverage

    Returns:
        Configured Task instance
    """
    import json

    metadata = matching_result.get("metadata", {})
    description, expected_output = extract_task_fields_from_prompt(
        context=context,
        prompt_name="resume_evaluation_user_prompt",
        model_class=ScreeningEvaluationOutput,
        format_kwargs={
            "application_id": matching_result["application_id"],
            "candidate_name": matching_result["candidate_name"],
            "job_title": matching_result["job_title"],
            "match_score": scoring_result["match_score"],
            "must_have_coverage": scoring_result["must_have_coverage"],
            "must_have_matches": scoring_result["must_have_matches"],
            "total_must_have_requirements": metadata.get("total_must_have_requirements", 0),
            "match_results": json.dumps(matching_result.get("match_results", []), indent=2),
        },
    )

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
        output_pydantic=ScreeningEvaluationOutput,
    )
