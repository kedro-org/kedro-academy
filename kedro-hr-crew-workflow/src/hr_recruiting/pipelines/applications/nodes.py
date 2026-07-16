"""Applications pipeline nodes - agentic processing with CrewAI."""

from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext

from datetime import datetime

from hr_recruiting.base.utils import (
    execute_crew_with_retry,
    extract_text_from_document,
    get_document_id,
    get_model_dump,
)
from hr_recruiting.pipelines.applications.agents import (
    create_resume_parser_agent,
)
from hr_recruiting.pipelines.applications.helper import extract_resume_parsing_result
from hr_recruiting.pipelines.applications.models import Application, ParsedResume
from hr_recruiting.pipelines.applications.tasks import create_resume_parsing_task


def parse_raw_resume(raw_resume_doc: Any) -> dict[str, Any]:
    """Extract text and candidate_id from raw resume document.
    
    Returns:
        ParsedResume model dumped to dict for Kedro dataset compatibility
    
    Raises:
        ValueError: If candidate_id cannot be extracted from document properties
    """
    raw_text = extract_text_from_document(raw_resume_doc)
    
    # Extract candidate_id from document properties
    # In production, we should use a more robust way to extract the candidate_id
    candidate_id = get_document_id(raw_resume_doc, "candidate_id")
    
    # Create and validate ParsedResume model using utility function
    return get_model_dump(
        ParsedResume,
        candidate_id=candidate_id,
        raw_resume_text=raw_text,
    )


def run_resume_parsing_crew(
    resume_parser_context: LLMContext,
    parsed_resume: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run CrewAI crew for resume parsing and normalization.
    
    Returns:
        Tuple of (candidate_profile, evidence_snippets)
    """
    # Extract fields from already-validated parsed_resume dict
    raw_resume_text = parsed_resume["raw_resume_text"]
    candidate_id = parsed_resume["candidate_id"]

    # Create agent
    resume_parser_agent = create_resume_parser_agent(resume_parser_context)

    # Create task (schema JSON is injected from Pydantic models in format_resume_parsing_prompt)
    task = create_resume_parsing_task(
        resume_parser_context,
        resume_parser_agent,
        raw_resume_text,
        candidate_id,
    )

    # Create crew
    crew = Crew(
        agents=[resume_parser_agent],
        tasks=[task],
        verbose=True,
        tracing=False,
    )

    # Execute crew with retry logic for connection errors
    result = execute_crew_with_retry(crew)

    # Extract and structure results (already validated against ResumeParsingOutput model)
    parsing_result = extract_resume_parsing_result(result)
    
    # Extract candidate_profile and evidence_snippets (guaranteed to exist from validation)
    return (parsing_result["candidate_profile"], parsing_result["evidence_snippets"])


def create_application(
    normalized_candidate_profile: dict[str, Any],
    job_metadata: dict[str, Any],
    evidence_snippets: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create Application object from candidate profile, job metadata, and evidence snippets.

    Args:
        normalized_candidate_profile: Validated CandidateProfile dictionary
        job_metadata: Validated JobMetadata dictionary
        evidence_snippets: Validated list of EvidenceSnippet dictionaries

    Returns:
        Application dictionary with application_id, job_id, candidate_id, artifacts, and evidence_snippets
    """
    # All inputs are already validated Pydantic models, so we can directly access fields
    candidate_id = normalized_candidate_profile["candidate_id"]
    candidate_name = normalized_candidate_profile["name"]
    
    job_id = job_metadata["job_id"]
    job_title = job_metadata["title"]
    location = job_metadata["location"]
    
    # This should be more robust in production 
    # by using a more unique identifier
    application_id = f"{candidate_id}_{job_id}"

    return get_model_dump(
        Application,
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
        evidence_snippets=evidence_snippets,
    )
