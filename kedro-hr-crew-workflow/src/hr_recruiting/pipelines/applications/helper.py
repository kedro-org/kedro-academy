"""Helper functions for applications pipeline.

This module contains helper functions used by the applications pipeline nodes
for resume parsing, prompt formatting, and result extraction.
"""

from typing import Any

from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.pipelines.applications.models import ResumeParsingOutput
from hr_recruiting.base.utils import (
    extract_task_outputs_from_crew_result,
    get_model_dump,
    parse_json_from_text,
)


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
    import json
    
    user_prompt = context.prompts.get("resume_parsing_user_prompt")
    if not user_prompt:
        raise ValueError("resume_parsing_user_prompt not found in LLMContext")
    
    # Get schema JSON from ResumeParsingOutput model (contains both candidate_profile and evidence_snippets)
    output_schema_json = json.dumps(
        ResumeParsingOutput.model_json_schema(), indent=2
    )
    
    try:
        # Extract the string content from prompt
        if isinstance(user_prompt, list) and user_prompt:
            prompt_str = str(user_prompt[-1].content if hasattr(user_prompt[-1], "content") else user_prompt[-1])
        else:
            prompt_str = str(user_prompt)
        
        # Replace double braces from YAML template ({{var}} -> value)
        replacements = {
            "{{raw_resume_text}}": raw_resume_text,
            "{{candidate_id}}": candidate_id,
            "{{output_schema}}": output_schema_json,
        }
        for placeholder, value in replacements.items():
            prompt_str = prompt_str.replace(placeholder, value)
        
        # Also handle single braces in case they weren't formatted
        single_brace_replacements = {
            "{raw_resume_text}": raw_resume_text,
            "{candidate_id}": candidate_id,
            "{output_schema}": output_schema_json,
        }
        for placeholder, value in single_brace_replacements.items():
            if placeholder in prompt_str:
                prompt_str = prompt_str.replace(placeholder, value)
        
        return prompt_str
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
    # Extract task outputs from crew result
    task_outputs = extract_task_outputs_from_crew_result(crew_result)
    
    if not task_outputs:
        raise ValueError("No task outputs found in crew result")
    
    # Get the final task output (should be the resume parsing result)
    task_output = str(task_outputs[-1])
    
    # Parse JSON from task output
    parsed = parse_json_from_text(task_output)
    
    if not parsed or not isinstance(parsed, dict):
        raise ValueError(f"Failed to parse JSON from task output: {task_output[:200]}")
    
    # Validate against ResumeParsingOutput model and convert to dict
    parsing_output_dict = get_model_dump(ResumeParsingOutput, **parsed)
    
    return parsing_output_dict
