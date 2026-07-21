"""Helper functions for applications pipeline.

This module contains helper functions used by the applications pipeline nodes
for resume parsing, prompt formatting, and result extraction.
"""

import json
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import extract_structured_task_output
from hr_recruiting.pipelines.applications.models import ResumeParsingOutput


def format_resume_parsing_prompt(
    context: LLMContext,
    raw_resume_text: str,
    candidate_id: str,
) -> str:
    """Format the resume parsing user prompt with actual values and schema JSON.

    Args:
        context: LLMContext containing prompts
        raw_resume_text: Raw resume text to include in prompt
        candidate_id: Candidate identifier to include in prompt

    Returns:
        Formatted prompt string with schema JSON injected

    Raises:
        ValueError: If prompt is missing or formatting fails
    """
    user_prompt = context.prompts.get("resume_parsing_user_prompt")
    if not user_prompt:
        raise ValueError("resume_parsing_user_prompt not found in LLMContext")

    output_schema_json = json.dumps(
        ResumeParsingOutput.model_json_schema(), indent=2
    )

    try:
        formatted = user_prompt.format(
            raw_resume_text=raw_resume_text,
            candidate_id=candidate_id,
            output_schema=output_schema_json,
        )
        if isinstance(formatted, list) and formatted:
            prompt_content = str(
                formatted[-1].content
                if hasattr(formatted[-1], "content")
                else formatted[-1]
            )
        else:
            prompt_content = str(formatted)

        return prompt_content.strip()
    except Exception as e:
        raise ValueError(f"Failed to format resume_parsing_user_prompt: {e}") from e


def extract_resume_parsing_result(
    crew_result: Any,
) -> dict[str, Any]:
    """Extract and structure resume parsing result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()

    Returns:
        Dictionary with "candidate_profile" and "evidence_snippets" keys
        
    Raises:
        ValueError: If crew result cannot be parsed or validated
    """
    return extract_structured_task_output(crew_result, ResumeParsingOutput)
