"""Task creation functions for screening pipeline.

This module contains factory functions for creating CrewAI tasks
used in the screening workflow.
"""

from typing import Any

from crewai import Agent, Task
from kedro.pipeline.llm_context import LLMContext

import json

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
    if user_prompt:
        try:
            formatted = user_prompt.format(must_have_requirements="", evidence_snippets="")
            prompt_content = str(formatted[-1].content if isinstance(formatted, list) and formatted and hasattr(formatted[-1], "content") else formatted)
        except Exception:
            prompt_content = str(user_prompt)
    else:
        prompt_content = ""
    
    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        description = "Match job requirements to evidence snippets"
    
    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        expected_output = "JSON object with application_id and match_results (array of match results with requirement, snippet_ids, and confidence scores)"

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
    
    formatted = user_prompt.format(
        job_requirements="",
        candidate_profile="",
        evidence_snippets="",
        match_results="",
        screening_result_schema_json=screening_result_schema_json,
    )
    prompt_content = str(formatted[-1].content if isinstance(formatted, list) and formatted and hasattr(formatted[-1], "content") else formatted)
    
    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        description = "Evaluate candidate resume against job posting"
    
    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        raise ValueError("expected_output not found in resume_evaluation_user_prompt")

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )


def create_email_draft_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create email draft task.

    Args:
        context: LLMContext containing prompts
        agent: Communications drafter agent

    Returns:
        Configured Task instance
    """
    # Get schema JSON from Pydantic model
    screening_result_schema_json = json.dumps(
        ScreeningResult.model_json_schema(), indent=2
    )
    
    # Format prompt with empty strings and schema JSON to extract content
    user_prompt = context.prompts.get("email_draft_user_prompt")
    if not user_prompt:
        raise ValueError("email_draft_user_prompt not found in context")
    
    formatted = user_prompt.format(
        candidate_name="",
        job_title="",
        recommendation="",
        match_score="",
        strengths="",
        gaps="",
        screening_result_schema_json=screening_result_schema_json,
    )
    prompt_content = str(formatted[-1].content if isinstance(formatted, list) and formatted and hasattr(formatted[-1], "content") else formatted)
    
    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        description = "Draft email communication"
    
    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        raise ValueError("expected_output not found in email_draft_user_prompt")

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )
