"""Task creation functions for screening pipeline.

This module contains factory functions for creating CrewAI tasks
used in the screening workflow.
"""

import json

from crewai import Agent, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import extract_field_from_prompt
from hr_recruiting.pipelines.screening.models import ScreeningResult


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
    # Format prompt with empty strings to extract content (same approach as applications pipeline)
    user_prompt = context.prompts.get("requirements_matching_user_prompt")
    if not user_prompt:
        raise ValueError("requirements_matching_user_prompt not found in context")
    
    try:
        formatted = user_prompt.format(must_have_requirements="", evidence_snippets="")
        # Extract the string content properly
        if isinstance(formatted, list) and formatted:
            prompt_content = str(formatted[-1].content if hasattr(formatted[-1], "content") else formatted[-1])
        else:
            prompt_content = str(formatted)
        
        # Strip leading/trailing whitespace and normalize line breaks
        prompt_content = prompt_content.strip()
    except Exception as e:
        raise ValueError(f"Error formatting requirements_matching_user_prompt: {e}") from e

    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        raise ValueError(f"description not found in requirements_matching_user_prompt. Prompt content preview: {prompt_content[:200]}")

    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        raise ValueError("expected_output not found in requirements_matching_user_prompt")

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
    # Get schema JSON from Pydantic model
    screening_result_schema_json = json.dumps(
        ScreeningResult.model_json_schema(), indent=2
    )

    # Format prompt with empty strings and schema JSON to extract content
    user_prompt = context.prompts.get("resume_evaluation_user_prompt")
    if not user_prompt:
        raise ValueError("resume_evaluation_user_prompt not found in context")

    try:
        formatted = user_prompt.format(
            job_requirements="",
            candidate_profile="",
            evidence_snippets="",
            match_results="",
            screening_result_schema_json=screening_result_schema_json,
        )
        # Extract the string content properly
        if isinstance(formatted, list) and formatted:
            prompt_content = str(formatted[-1].content if hasattr(formatted[-1], "content") else formatted[-1])
        else:
            prompt_content = str(formatted)
        
        # Strip leading/trailing whitespace and normalize line breaks
        prompt_content = prompt_content.strip()
    except Exception as e:
        raise ValueError(f"Error formatting resume_evaluation_user_prompt: {e}") from e

    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        raise ValueError(f"description not found in resume_evaluation_user_prompt. Prompt content preview: {prompt_content[:200]}")

    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        raise ValueError("expected_output not found in resume_evaluation_user_prompt")

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )
