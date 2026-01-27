"""Helper functions for applications pipeline.

This module contains helper functions used by the applications pipeline nodes
for resume parsing, prompt formatting, and result extraction.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.pipelines.applications.models import Application, CandidateProfile, EvidenceSnippet
from hr_recruiting.base.utils import (
    extract_task_outputs_from_crew_result,
    parse_json_from_text,
)


def build_resume_parsing_preview() -> str:
    """Read and return agents.py file content.
    
    Returns:
        Content of agents.py file as string
    """
    # Get the path to agents.py file relative to this helper file
    current_file = Path(__file__)
    agents_file = current_file.parent / "agents.py"
    
    # Read the agents.py file content
    try:
        agents_content = agents_file.read_text()
    except FileNotFoundError:
        agents_content = "agents.py file not found"
    
    return agents_content


def create_application(
    normalized_candidate_profile: dict[str, Any],
    job_metadata: dict[str, Any],
    evidence_snippets: dict[str, Any],
) -> dict[str, Any]:
    """Create Application object from candidate profile, job metadata, and evidence snippets.

    Args:
        normalized_candidate_profile: Normalized candidate profile dictionary
        job_metadata: Job metadata dictionary with job_id, title, location
        evidence_snippets: Dictionary with candidate_id, candidate_name, and snippets array

    Returns:
        Application dictionary with application_id, job_id, candidate_id, artifacts, and evidence_snippets
    """
    # Validate required fields - fail if missing
    if "candidate_id" not in normalized_candidate_profile:
        raise ValueError("candidate_id not found in normalized_candidate_profile")
    candidate_id = normalized_candidate_profile["candidate_id"]
    
    if "job_id" not in job_metadata:
        raise ValueError("job_id not found in job_metadata")
    job_id = job_metadata["job_id"]
    
    application_id = f"{candidate_id}_{job_id}"

    # Extract candidate_name and job_title for use in email drafting
    if "name" not in normalized_candidate_profile:
        raise ValueError("name not found in normalized_candidate_profile")
    candidate_name = normalized_candidate_profile["name"]
    
    if "title" not in job_metadata:
        raise ValueError("title not found in job_metadata")
    job_title = job_metadata["title"]
    
    if "location" not in job_metadata:
        raise ValueError("location not found in job_metadata")
    location = job_metadata["location"]

    # Extract evidence snippets list
    if "snippets" not in evidence_snippets:
        raise ValueError("snippets not found in evidence_snippets")
    snippets_list = evidence_snippets["snippets"]
    
    # Validate snippets are EvidenceSnippet objects
    validated_snippets = []
    for snippet_data in snippets_list:
        try:
            snippet = EvidenceSnippet(**snippet_data)
            validated_snippets.append(snippet)
        except Exception as e:
            raise ValueError(f"Invalid evidence snippet: {e}") from e

    application = Application(
        application_id=application_id,
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        submitted_at=datetime.now(),
        status="pending",
        artifacts={
            "job_id": job_id,
            "job_title": job_title,
            "location": location,
        },
        evidence_snippets=validated_snippets,
    )

    # Use mode='json' to serialize datetime objects to ISO format strings
    return application.model_dump(mode='json')


def format_schema_info(schema_template: dict[str, Any]) -> str:
    """Format schema information using template with dynamic schema JSON.

    Args:
        schema_template: Schema template dictionary from YAML dataset

    Returns:
        Formatted string with schema information
    """
    import json
    
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
    
    # Get schema JSON from Pydantic models
    candidate_profile_schema_json = json.dumps(
        CandidateProfile.model_json_schema(), indent=2
    )
    evidence_snippets_schema_json = json.dumps(
        EvidenceSnippet.model_json_schema(), indent=2
    )
    
    try:
        # Try formatting with LangChain's format method first
        formatted_prompt = user_prompt.format(
            raw_resume_text=raw_resume_text,
            candidate_id=candidate_id,
            candidate_profile_schema_json=candidate_profile_schema_json,
            evidence_snippets_schema_json=evidence_snippets_schema_json,
        )
        
        # Extract the string content
        if isinstance(formatted_prompt, list) and formatted_prompt:
            prompt_str = str(formatted_prompt[-1].content if hasattr(formatted_prompt[-1], "content") else formatted_prompt[-1])
        else:
            prompt_str = str(formatted_prompt)
        
        # Handle double braces in YAML templates ({{var}} -> {var} for Python format, then replace)
        # If formatting didn't work (double braces weren't replaced), manually replace them
        replacements = {
            "{{raw_resume_text}}": raw_resume_text,
            "{{candidate_id}}": candidate_id,
            "{{candidate_profile_schema_json}}": candidate_profile_schema_json,
            "{{evidence_snippets_schema_json}}": evidence_snippets_schema_json,
        }
        for placeholder, value in replacements.items():
            if placeholder in prompt_str:
                prompt_str = prompt_str.replace(placeholder, value)
        
        # Also handle single braces in case they weren't formatted
        single_brace_replacements = {
            "{raw_resume_text}": raw_resume_text,
            "{candidate_id}": candidate_id,
            "{candidate_profile_schema_json}": candidate_profile_schema_json,
            "{evidence_snippets_schema_json}": evidence_snippets_schema_json,
        }
        for placeholder, value in single_brace_replacements.items():
            if placeholder in prompt_str:
                prompt_str = prompt_str.replace(placeholder, value)
        
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


def create_candidate_profile(
    candidate_data: dict[str, Any],
    raw_resume_text: str = "",
) -> dict[str, Any]:
    """Create CandidateProfile model from structured data.

    Args:
        candidate_data: Extracted candidate profile data
        raw_resume_text: Original resume text for validation

    Returns:
        CandidateProfile dictionary (validated model dumped to dict) or None if validation fails
    """
    # Ensure raw_resume_text is included
    if raw_resume_text:
        candidate_data = validate_extracted_data(candidate_data, raw_resume_text)
    
    # Validate and create CandidateProfile model
    try:
        candidate_profile = CandidateProfile(**candidate_data)
        return candidate_profile.model_dump()
    except Exception as e:
        # Log error but continue with the data
        print(f"Error validating candidate_profile: {e}")  # noqa: T201
        return candidate_data




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
    
    # Create CandidateProfile model using helper function
    return create_candidate_profile(candidate_data, raw_resume_text)


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
    candidate_id: str = "unknown",
) -> dict[str, Any]:
    """Extract and structure resume parsing result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()
        raw_resume_text: Original resume text for validation
        candidate_id: Candidate identifier to add to evidence snippets

    Returns:
        Dictionary with "candidate_profile" and "evidence_snippets" keys
    """
    result = {
        "candidate_profile": None,
        "evidence_snippets": {
            "candidate_id": candidate_id,
            "candidate_name": "Unknown",
            "snippets": [],
        },
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
        candidate_profile = _extract_candidate_profile(parsed, raw_resume_text)
        result["candidate_profile"] = candidate_profile
        
        # Extract candidate_name from profile for evidence_snippets
        candidate_name = "Unknown"
        if candidate_profile and isinstance(candidate_profile, dict):
            candidate_name = candidate_profile.get("name", "Unknown")
        
        # Extract evidence snippets
        snippets = _extract_evidence_snippets(parsed)
        
        # Structure evidence_snippets with candidate_id and candidate_name as root keys
        result["evidence_snippets"] = {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "snippets": snippets,
        }

    except Exception as e:
        print(f"Error parsing crew result: {e}")  # noqa: T201

    return result
