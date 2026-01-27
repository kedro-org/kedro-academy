"""Applications pipeline nodes - agentic processing with CrewAI."""

from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext
from kedro.pipeline.preview_contract import TextPreview

from hr_recruiting.base.utils import execute_crew_with_retry, extract_text_from_document
from hr_recruiting.pipelines.applications.agents import (
    create_resume_parser_agent_with_tools,
)
from hr_recruiting.pipelines.applications.helper import (
    build_resume_parsing_preview,
    extract_resume_parsing_result,
)
from hr_recruiting.pipelines.applications.tasks import create_resume_parsing_task


def preview_resume_parsing_crew() -> TextPreview:
    """Preview function showing agents.py file content."""
    agents_content = build_resume_parsing_preview()
    
    return TextPreview(
        content=agents_content,
        meta={
            "language": "python"
        }
    )


def parse_resume_text(raw_resume_doc: Any) -> dict[str, Any]:
    """Extract text and candidate_id from raw resume document.
    
    Raises:
        ValueError: If candidate_id cannot be extracted from document properties
    """
    raw_text = extract_text_from_document(raw_resume_doc)
    
    # Try to extract candidate_id from document properties
    candidate_id = None
    if hasattr(raw_resume_doc.core_properties, "title") and raw_resume_doc.core_properties.title:
        candidate_id = raw_resume_doc.core_properties.title
    elif hasattr(raw_resume_doc.core_properties, "subject") and raw_resume_doc.core_properties.subject:
        candidate_id = raw_resume_doc.core_properties.subject
    
    if not candidate_id:
        raise ValueError("candidate_id not found in resume document properties (title or subject)")
    
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

    # Get raw resume text and candidate_id - fail if missing
    if "raw_resume_text" not in parsed_resume:
        raise ValueError("raw_resume_text not found in parsed_resume")
    raw_resume_text = parsed_resume["raw_resume_text"]
    
    if "candidate_id" not in parsed_resume:
        raise ValueError("candidate_id not found in parsed_resume")
    candidate_id = parsed_resume["candidate_id"]

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
    """Split resume parsing result into candidate profile and evidence snippets.
    
    Raises:
        ValueError: If required fields are missing
    """
    if "candidate_profile" not in resume_parsing_result:
        raise ValueError("candidate_profile not found in resume_parsing_result")
    candidate_profile = resume_parsing_result["candidate_profile"]
    
    if "evidence_snippets" not in resume_parsing_result:
        raise ValueError("evidence_snippets not found in resume_parsing_result")
    evidence_snippets = resume_parsing_result["evidence_snippets"]
    
    # Validate evidence_snippets structure
    if not isinstance(evidence_snippets, dict):
        raise ValueError("evidence_snippets must be a dictionary")
    if "candidate_id" not in evidence_snippets:
        raise ValueError("candidate_id not found in evidence_snippets")
    if "candidate_name" not in evidence_snippets:
        raise ValueError("candidate_name not found in evidence_snippets")
    if "snippets" not in evidence_snippets:
        raise ValueError("snippets not found in evidence_snippets")
    
    return (candidate_profile, evidence_snippets)
