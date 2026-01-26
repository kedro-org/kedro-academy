"""Helper functions for applications pipeline.

This module contains helper functions used by the applications pipeline nodes
for resume parsing, prompt formatting, and result extraction.
"""

import json
import re
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.models import CandidateProfile, EvidenceSnippet
from hr_recruiting.base.utils import extract_task_outputs_from_crew_result


def parse_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON from text that may contain markdown or other formatting.

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    if not text:
        return None

    # Try to find JSON in code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object directly
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try parsing the entire text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def format_schema_info(schema_template: dict[str, Any]) -> str:
    """Format schema information using template with dynamic schema JSON.

    Args:
        schema_template: Schema template dictionary from YAML dataset

    Returns:
        Formatted string with schema information
    """
    try:
        # Get dynamic schemas from Pydantic models
        candidate_profile_schema_json = json.dumps(
            CandidateProfile.model_json_schema(), indent=2
        )
        evidence_snippets_schema_json = json.dumps(
            EvidenceSnippet.model_json_schema(), indent=2
        )

        # Format candidate profile schema
        candidate_profile_desc = schema_template["candidate_profile_schema"]["description"].format(
            candidate_profile_schema_json=candidate_profile_schema_json
        )

        # Format evidence snippets schema
        evidence_snippets_desc = schema_template["evidence_snippets_schema"]["description"].format(
            evidence_snippets_schema_json=evidence_snippets_schema_json
        )

        # Get output format instructions
        output_format_desc = schema_template["output_format"]["description"]

        # Combine all schema information with proper spacing
        schema_sections = [
            candidate_profile_desc,
            evidence_snippets_desc,
            output_format_desc,
        ]
        return "\n\n".join(section.strip() for section in schema_sections if section.strip())
    except KeyError as e:
        print(f"Error: Missing key in schema template: {e}")  # noqa: T201
        print(f"Available keys: {list(schema_template.keys())}")  # noqa: T201
        raise
    except Exception as e:
        print(f"Error formatting schema info: {e}")  # noqa: T201
        raise


def format_resume_parsing_prompt(
    context: LLMContext,
    raw_resume_text: str,
    candidate_id: str,
) -> str:
    """Format the resume parsing user prompt with actual values.

    Args:
        context: LLMContext containing prompts
        raw_resume_text: Raw resume text to include in prompt
        candidate_id: Candidate identifier to include in prompt

    Returns:
        Formatted prompt string

    Raises:
        ValueError: If prompt is missing or formatting fails
    """
    user_prompt = context.prompts.get("resume_parsing_user_prompt")
    if not user_prompt:
        raise ValueError("resume_parsing_user_prompt not found in LLMContext")
    
    try:
        # Try formatting with LangChain's format method first
        formatted_prompt = user_prompt.format(
            raw_resume_text=raw_resume_text,
            candidate_id=candidate_id,
        )
        
        # Extract the string content
        if isinstance(formatted_prompt, list) and formatted_prompt:
            prompt_str = str(formatted_prompt[-1].content if hasattr(formatted_prompt[-1], "content") else formatted_prompt[-1])
        else:
            prompt_str = str(formatted_prompt)
        
        # Handle double braces in YAML templates ({{var}} -> {var} for Python format, then replace)
        # If formatting didn't work (double braces weren't replaced), manually replace them
        if "{{raw_resume_text}}" in prompt_str or "{{candidate_id}}" in prompt_str:
            prompt_str = prompt_str.replace("{{raw_resume_text}}", raw_resume_text)
            prompt_str = prompt_str.replace("{{candidate_id}}", candidate_id)
        
        # Also handle single braces in case they weren't formatted
        if "{raw_resume_text}" in prompt_str or "{candidate_id}" in prompt_str:
            prompt_str = prompt_str.replace("{raw_resume_text}", raw_resume_text)
            prompt_str = prompt_str.replace("{candidate_id}", candidate_id)
        
        return prompt_str
    except Exception as e:
        raise ValueError(f"Failed to format resume_parsing_user_prompt: {e}") from e


def validate_extracted_data(
    candidate_data: dict[str, Any],
    raw_resume_text: str,
) -> dict[str, Any]:
    """Validate that extracted data conforms to expected structure.

    Args:
        candidate_data: Extracted candidate profile data
        raw_resume_text: Original resume text for reference

    Returns:
        Validated candidate data with raw_resume_text preserved
    """
    validated = candidate_data.copy()
    validated["raw_resume_text"] = raw_resume_text
    return validated




def _extract_candidate_profile(
    parsed: dict[str, Any],
    raw_resume_text: str,
) -> dict[str, Any] | None:
    """Extract and validate candidate profile from parsed data.

    Args:
        parsed: Parsed JSON dictionary from agent output
        raw_resume_text: Original resume text for validation

    Returns:
        Validated candidate profile dictionary or None
    """
    if "candidate_profile" not in parsed:
        return None
    
    candidate_data = parsed["candidate_profile"]
    
    # Validate structure and preserve raw_resume_text
    if raw_resume_text:
        candidate_data = validate_extracted_data(candidate_data, raw_resume_text)
    
    # Validate and return candidate_profile
    try:
        candidate_profile = CandidateProfile(**candidate_data)
        return candidate_profile.model_dump()
    except Exception as e:
        # Log error but continue with the data
        print(f"Error validating candidate_profile: {e}")  # noqa: T201
        return candidate_data


def _extract_evidence_snippets(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and validate evidence snippets from parsed data.

    Args:
        parsed: Parsed JSON dictionary from agent output

    Returns:
        List of validated evidence snippet dictionaries
    """
    if "evidence_snippets" not in parsed:
        return []
    
    snippets_data = parsed["evidence_snippets"]
    if not isinstance(snippets_data, list):
        return []
    
    validated_snippets = []
    for snippet_data in snippets_data:
        try:
            snippet = EvidenceSnippet(**snippet_data)
            validated_snippets.append(snippet.model_dump())
        except Exception:
            # Include even if validation fails
            validated_snippets.append(snippet_data)
    
    return validated_snippets


def extract_resume_parsing_result(
    crew_result: Any,
    raw_resume_text: str = "",
) -> dict[str, Any]:
    """Extract and structure resume parsing result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()
        raw_resume_text: Original resume text for validation

    Returns:
        Dictionary with "candidate_profile" and "evidence_snippets" keys
    """
    result = {
        "candidate_profile": None,
        "evidence_snippets": [],
    }

    try:
        # Extract task outputs from crew result
        task_outputs = extract_task_outputs_from_crew_result(crew_result)
        
        if not task_outputs:
            return result
        
        # Get the final task output (should be the resume parsing result)
        task_output = task_outputs[-1]
        
        # Parse JSON from task output
        output_str = str(task_output)
        parsed = parse_json_from_text(output_str)
        
        if not parsed or not isinstance(parsed, dict):
            return result
        
        # Extract candidate profile
        result["candidate_profile"] = _extract_candidate_profile(parsed, raw_resume_text)
        
        # Extract evidence snippets
        result["evidence_snippets"] = _extract_evidence_snippets(parsed)

    except Exception as e:
        print(f"Error parsing crew result: {e}")  # noqa: T201

    return result
