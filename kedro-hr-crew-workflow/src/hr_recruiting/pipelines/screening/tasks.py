"""Task creation functions for screening pipeline.

This module contains factory functions for creating CrewAI tasks
used in the screening workflow.
"""

from crewai import Agent, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.pipelines.screening.helper import extract_task_fields_from_prompt
from hr_recruiting.pipelines.screening.models import (
    RequirementsMatchingResult,
    ScreeningResult,
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
    )


def create_resume_evaluation_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create resume evaluation task.

    Args:
        context: LLMContext containing prompts
        agent: Resume evaluator agent

    Returns:
        Configured Task instance
    """
    description, expected_output = extract_task_fields_from_prompt(
        context=context,
        prompt_name="resume_evaluation_user_prompt",
        model_class=ScreeningResult,
        format_kwargs={
            "match_results": "",
        },
    )

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )
