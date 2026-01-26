"""Applications pipeline nodes - agentic processing with CrewAI."""

import os
from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import execute_crew_with_retry, extract_text_from_document
from hr_recruiting.pipelines.applications.agents import (
    create_resume_parser_agent_with_tools,
)
from hr_recruiting.pipelines.applications.helper import extract_resume_parsing_result
from hr_recruiting.pipelines.applications.tasks import create_resume_parsing_task

# Disable CrewAI telemetry to avoid connection errors
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"


def parse_resume_text(raw_resume_doc: Any) -> dict[str, Any]:
    """Extract text and candidate_id from raw resume document."""
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
) -> dict[str, Any]:
    """Run CrewAI crew for resume parsing and normalization."""
    # Create agent
    agent = create_resume_parser_agent_with_tools(resume_parser_context)

    # Get raw resume text and candidate_id
    raw_resume_text = parsed_resume.get("raw_resume_text", "")
    candidate_id = parsed_resume.get("candidate_id", "unknown")

    # Create task (schema JSON is injected from Pydantic models in format_resume_parsing_prompt)
    task = create_resume_parsing_task(
        resume_parser_context,
        agent,
        raw_resume_text,
        candidate_id,
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
    parsed_result = extract_resume_parsing_result(result, raw_resume_text, candidate_id)
    
    # Ensure candidate_id is set correctly
    if parsed_result.get("candidate_profile"):
        parsed_result["candidate_profile"]["candidate_id"] = candidate_id
        parsed_result["candidate_profile"]["raw_resume_text"] = raw_resume_text

    return parsed_result


def split_resume_parsing_result(
    resume_parsing_result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split resume parsing result into candidate profile and evidence snippets."""
    candidate_profile = resume_parsing_result.get("candidate_profile") or {}
    evidence_snippets = resume_parsing_result.get("evidence_snippets") or {
        "candidate_id": "unknown",
        "candidate_name": "Unknown",
        "snippets": [],
    }
    return (candidate_profile, evidence_snippets)
