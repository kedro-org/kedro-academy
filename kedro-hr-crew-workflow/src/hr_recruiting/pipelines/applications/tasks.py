"""Task creation functions for applications pipeline.

This module contains factory functions for creating CrewAI tasks
used in the resume parsing workflow.
"""

from crewai import Agent, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import extract_field_from_prompt
from hr_recruiting.pipelines.applications.helper import format_resume_parsing_prompt


def create_resume_parsing_task(
    context: LLMContext,
    agent: Agent,
    raw_resume_text: str,
    candidate_id: str,
) -> Task:
    """Create resume parsing task.

    Args:
        context: LLMContext containing prompts
        agent: Resume parser agent
        raw_resume_text: Raw resume text to parse
        candidate_id: Candidate identifier

    Returns:
        Configured Task instance
    """
    # Format the prompt with actual values and schema JSON (schema is injected from Pydantic models)
    task_description = format_resume_parsing_prompt(
        context,
        raw_resume_text,
        candidate_id,
    )
    
    # Extract expected_output from the formatted prompt string
    expected_output = extract_field_from_prompt(task_description, "expected_output")
    if not expected_output:
        raise ValueError("expected_output not found in resume_parsing_user_prompt")

    return Task(
        description=task_description,
        agent=agent,
        expected_output=expected_output,
    )
