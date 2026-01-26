"""Helper functions for screening pipeline.

This module contains helper functions used by the screening pipeline nodes
for crew orchestration, task creation, and result extraction.
"""

import json
from datetime import datetime
from typing import Any

from hr_recruiting.pipelines.screening.models import Application, EmailDraft, MatchResult, ScreeningResult
from hr_recruiting.base.utils import (
    extract_task_outputs_from_crew_result,
    parse_json_from_text,
)



def create_application(
    normalized_candidate_profile: dict[str, Any],
    normalized_job_posting: dict[str, Any],
) -> dict[str, Any]:
    """Create Application object from candidate profile and job posting.

    Args:
        normalized_candidate_profile: Normalized candidate profile dictionary
        normalized_job_posting: Normalized job posting dictionary

    Returns:
        Application dictionary with application_id, job_id, candidate_id, and artifacts
    """
    candidate_id = normalized_candidate_profile.get("candidate_id", "unknown")
    job_id = normalized_job_posting.get("job_id", "unknown")
    application_id = f"{candidate_id}_{job_id}"
    
    # Extract candidate_name and job_title for use in email drafting
    candidate_name = normalized_candidate_profile.get("name", "Candidate")
    job_title = normalized_job_posting.get("title", "Position")
    
    application = Application(
        application_id=application_id,
        job_id=job_id,
        candidate_id=candidate_id,
        submitted_at=datetime.now(),
        status="pending",
        artifacts={
            "candidate_name": candidate_name,
            "job_title": job_title,
        },
    )
    
    # Use mode='json' to serialize datetime objects to ISO format strings
    return application.model_dump(mode='json')


def extract_match_results(task_output: str) -> list[dict[str, Any]]:
    """Extract and validate match results from requirements matching task output.

    Args:
        task_output: Output from requirements matching task

    Returns:
        List of validated match result dictionaries
    """
    match_results = []
    
    # Try to parse as JSON first
    parsed = parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        if "match_results" in parsed:
            raw_results = parsed["match_results"]
            # Validate each match result
            for raw_result in raw_results:
                try:
                    match_result = MatchResult(**raw_result)
                    match_results.append(match_result.model_dump())
                except Exception:
                    # Include even if validation fails
                    match_results.append(raw_result)
        elif isinstance(parsed, list):
            # Handle case where tool returns list directly (backward compatibility)
            for raw_result in parsed:
                try:
                    match_result = MatchResult(**raw_result)
                    match_results.append(match_result.model_dump())
                except Exception:
                    match_results.append(raw_result)
    
    return match_results


def extract_application_id(task_output: str) -> str | None:
    """Extract application_id from requirements matching task output.

    Args:
        task_output: Output from requirements matching task

    Returns:
        Application ID string or None if not found
    """
    parsed = parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        return parsed.get("application_id")
    return None


def extract_evaluation_data(task_output: str) -> dict[str, Any]:
    """Extract evaluation data from resume evaluation task output.

    Args:
        task_output: Output from resume evaluation task

    Returns:
        Dictionary with match_score, must_have_coverage, gaps, strengths, risk_flags, recommendation, qa_suggestions
    """
    evaluation_data = {
        "match_score": 0.0,
        "must_have_coverage": 0.0,
        "gaps": [],
        "strengths": [],
        "risk_flags": [],
        "recommendation": "review",
        "qa_suggestions": [],
    }
    
    # Try to parse as JSON first
    parsed = parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        evaluation_data.update({
            "match_score": float(parsed.get("match_score", 0.0)),
            "must_have_coverage": float(parsed.get("must_have_coverage", 0.0)),
            "gaps": parsed.get("gaps", []),
            "strengths": parsed.get("strengths", []),
            "risk_flags": parsed.get("risk_flags", []),
            "recommendation": parsed.get("recommendation", "review"),
            "qa_suggestions": parsed.get("qa_suggestions", []),
        })
    
    return evaluation_data


def extract_email_draft(task_output: str) -> dict[str, Any]:
    """Extract and validate email draft from communications drafter task output.

    Args:
        task_output: Output from email draft task

    Returns:
        Validated email draft dictionary with subject, body, and placeholders
    """
    email_draft = {
        "subject": "Application Update",
        "body": "",
        "placeholders": {},
    }
    
    # Try to parse as JSON first
    parsed = parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        # Check if email_draft is nested
        if "email_draft" in parsed:
            raw_draft = parsed["email_draft"]
        else:
            raw_draft = parsed
        
        # Validate using EmailDraft model
        email_draft_obj = EmailDraft(**raw_draft)
        email_draft = email_draft_obj.model_dump()
    
    return email_draft


def extract_screening_result(crew_result: Any) -> dict[str, Any]:
    """Extract and structure screening result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()

    Returns:
        Structured screening result dictionary matching ScreeningResult schema
    """
    # Initialize default values
    screening_result = {
        "application_id": "unknown_unknown",
        "match_score": 0.0,
        "must_have_coverage": 0.0,
        "gaps": [],
        "strengths": [],
        "risk_flags": [],
        "recommendation": "review",
        "email_draft": None,
        "qa_suggestions": [],
        "match_results": [],
    }
    
    try:
        # Extract task outputs from crew result using shared utility
        task_outputs = extract_task_outputs_from_crew_result(crew_result)
        
        if not task_outputs:
            return screening_result
        
        # First, try to parse the final output as a complete ScreeningResult
        # (since we instructed the final task to output in ScreeningResult format)
        if task_outputs:
            final_output = str(task_outputs[-1]) if task_outputs else ""
            parsed_result = parse_json_from_text(final_output)
            
            # If we got a complete ScreeningResult, validate and use it
            # Check for required ScreeningResult fields before validation
            if parsed_result and isinstance(parsed_result, dict):
                required_fields = ["application_id", "match_score", "must_have_coverage", "recommendation"]
                if all(field in parsed_result for field in required_fields):
                    # Validate against ScreeningResult schema - strict validation
                    validated = ScreeningResult(**parsed_result)
                    return validated.model_dump()
        
        # Process individual task outputs (assuming order: requirements, evaluation, email)
        if len(task_outputs) >= 1:
            # First task: requirements matching
            first_task_output = str(task_outputs[0])
            match_results = extract_match_results(first_task_output)
            screening_result["match_results"] = match_results
            
            # Extract application_id from first task output (generated by tool)
            application_id = extract_application_id(first_task_output)
            if application_id:
                screening_result["application_id"] = application_id
        
        if len(task_outputs) >= 2:
            # Second task: resume evaluation
            second_task_output = str(task_outputs[1])
            eval_data = extract_evaluation_data(second_task_output)
            screening_result.update(eval_data)
        
        if len(task_outputs) >= 3:
            # Third task: email draft (or complete ScreeningResult)
            final_output_str = str(task_outputs[2])
            parsed = parse_json_from_text(final_output_str)
            
            if parsed and isinstance(parsed, dict):
                # Check if it's a complete ScreeningResult (must have all required fields)
                required_fields = ["application_id", "match_score", "must_have_coverage", "recommendation"]
                if all(field in parsed for field in required_fields):
                    # Validate against ScreeningResult schema - strict validation
                    validated = ScreeningResult(**parsed)
                    return validated.model_dump()
                
                # Otherwise, extract just email_draft
                if "email_draft" in parsed:
                    screening_result["email_draft"] = parsed["email_draft"]
                else:
                    email_draft = extract_email_draft(final_output_str)
                    screening_result["email_draft"] = email_draft
            else:
                email_draft = extract_email_draft(final_output_str)
                screening_result["email_draft"] = email_draft
        
    except Exception as e:
        # Re-raise exception to make failures visible
        raise ValueError(f"Error parsing crew result: {e}") from e
    
    # Ensure all required fields have valid defaults
    if screening_result["email_draft"] is None:
        screening_result["email_draft"] = {
            "subject": "Application Update",
            "body": "Thank you for your application.",
            "placeholders": {},
        }
    
    return screening_result
