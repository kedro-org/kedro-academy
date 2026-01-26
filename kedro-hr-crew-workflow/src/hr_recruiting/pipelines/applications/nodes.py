"""Applications pipeline nodes - agentic processing with CrewAI."""

import os
from typing import Any

from crewai import Crew, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import execute_crew_with_retry, extract_text_from_document
from hr_recruiting.pipelines.applications.agents import (
    create_resume_parser_agent_with_tools,
)
from hr_recruiting.pipelines.applications.helper import (
    extract_resume_parsing_result,
    format_resume_parsing_prompt,
    format_schema_info,
)

# Disable CrewAI telemetry to avoid connection errors
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"


def parse_resume_text(raw_resume_doc: Any) -> dict[str, Any]:
    """Extract text and candidate_id from raw resume document.

    Args:
        raw_resume_doc: python-docx Document object

    Returns:
        Dictionary with candidate_id and raw_resume_text
    """
    raw_text = extract_text_from_document(raw_resume_doc)
    
    candidate_id = "unknown"
    if hasattr(raw_resume_doc.core_properties, "title") and raw_resume_doc.core_properties.title:
        candidate_id = raw_resume_doc.core_properties.title
    elif hasattr(raw_resume_doc.core_properties, "subject") and raw_resume_doc.core_properties.subject:
        candidate_id = raw_resume_doc.core_properties.subject
    
    return {
        "candidate_id": candidate_id,
        "raw_resume_text": raw_text,
    }


def run_resume_parsing_crew(
    resume_parser_context: LLMContext,
    parsed_resume: dict[str, Any],
    resume_parsing_schema_template: dict[str, Any],
) -> dict[str, Any]:
    """Run CrewAI crew for resume parsing and normalization.

    This function creates a single-agent crew that:
    1. Parses raw resume text
    2. Extracts structured candidate information
    3. Normalizes to CandidateProfile format
    4. Extracts evidence snippets

    Args:
        resume_parser_context: LLMContext for resume parser agent
        parsed_resume: Parsed resume data with raw_resume_text and candidate_id
        resume_parsing_schema_template: Schema template dictionary from YAML dataset

    Returns:
        Dictionary with "candidate_profile" and "evidence_snippets" keys
    """
    # Create agent
    agent = create_resume_parser_agent_with_tools(resume_parser_context)

    # Get raw resume text and candidate_id
    raw_resume_text = parsed_resume.get("raw_resume_text", "")
    candidate_id = parsed_resume.get("candidate_id", "unknown")

    # Format the prompt with actual values
    task_description = format_resume_parsing_prompt(
        resume_parser_context,
        raw_resume_text,
        candidate_id,
    )

    # Add schema information to task description from template
    schema_info = format_schema_info(resume_parsing_schema_template)
    task_description += f"\n\n{schema_info}"

    # Create task
    task = Task(
        description=task_description,
        agent=agent,
        expected_output="A JSON object with 'candidate_profile' and 'evidence_snippets' keys, both matching their respective schemas.",
    )

    # Create crew
    crew = Crew(
        agents=[agent],
        tasks=[task],
        verbose=True,
        tracing=False,
    )

    # Execute crew with retry logic for connection errors
    result = execute_crew_with_retry(crew)

    # Extract and structure results
    parsed_result = extract_resume_parsing_result(result, raw_resume_text)
    
    # Ensure candidate_id is set correctly
    if parsed_result.get("candidate_profile"):
        parsed_result["candidate_profile"]["candidate_id"] = candidate_id
        parsed_result["candidate_profile"]["raw_resume_text"] = raw_resume_text

    return parsed_result


def split_resume_parsing_result(
    resume_parsing_result: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Split resume parsing result into separate candidate profile and evidence snippets.

    Args:
        resume_parsing_result: Dictionary with "candidate_profile" and "evidence_snippets" keys

    Returns:
        Tuple of (candidate_profile dict, evidence_snippets list)
    """
    candidate_profile = resume_parsing_result.get("candidate_profile") or {}
    evidence_snippets = resume_parsing_result.get("evidence_snippets") or []
    return (candidate_profile, evidence_snippets)
