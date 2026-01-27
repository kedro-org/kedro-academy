"""Helper functions for screening pipeline.

This module contains helper functions used by the screening pipeline nodes
for crew orchestration, task creation, and result extraction.
"""

from typing import Any

from hr_recruiting.pipelines.screening.models import MatchResult, ScreeningResult
from hr_recruiting.base.utils import (
    extract_task_outputs_from_crew_result,
    parse_json_from_text,
)


def build_screening_graph() -> str:
    """Build simple Mermaid diagram showing context, agents, and tools.
    
    Returns:
        Mermaid diagram string
    """
    return """graph TD
    
    CTX1Inputs[LLM + Prompts + Requirements Matcher Tool] --> CTX1[Requirements Matcher Context]
    AGENT1[RequirementsMatcherAgent + RequirementsMatchingTask]
    CTX1 --> AGENT1
    AGENT1OUTPUT[MatchingResults]
    AGENT1 --> AGENT1OUTPUT
    
    
    CTXInputs[LLM + Prompts + Scoring Tool] --> CTX2[Resume Evaluator Context]
    AGENT2[ResumeEvaluatorAgent + ResumeEvaluationTask]
    AGENT1OUTPUT --> AGENT2
    CTX2 --> AGENT2
    AGENT2OUTPUT[EvaluationResults]
    AGENT2 --> AGENT2OUTPUT
    
    AGENT2OUTPUT --> OUTPUT[ScreeningResult]
    
    style CTX1 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style CTX2 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style AGENT1 fill:#50C878,stroke:#2D8659,stroke-width:2px,color:#fff
    style AGENT2 fill:#50C878,stroke:#2D8659,stroke-width:2px,color:#fff
    style OUTPUT fill:#6C5CE7,stroke:#4A3FA8,stroke-width:2px,color:#fff"""


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


def extract_application_info(task_output: str) -> dict[str, str]:
    """Extract application info from requirements matching task output.

    Args:
        task_output: Output from requirements matching task

    Returns:
        Dictionary with application_id, candidate_name, and job_title

    Raises:
        ValueError: If required fields are missing
    """
    parsed = parse_json_from_text(task_output)
    if not parsed or not isinstance(parsed, dict):
        raise ValueError("Could not parse task output as JSON dictionary")
    
    required_fields = ["application_id", "candidate_name", "job_title"]
    missing_fields = [f for f in required_fields if f not in parsed]
    if missing_fields:
        raise ValueError(f"Missing required fields in task output: {missing_fields}")
    
    return {
        "application_id": parsed["application_id"],
        "candidate_name": parsed["candidate_name"],
        "job_title": parsed["job_title"],
    }


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


def extract_screening_result(crew_result: Any) -> dict[str, Any]:
    """Extract and structure screening result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()

    Returns:
        Structured screening result dictionary matching ScreeningResult schema

    Raises:
        ValueError: If required fields are missing or validation fails
    """
    try:
        # Extract task outputs from crew result using shared utility
        task_outputs = extract_task_outputs_from_crew_result(crew_result)

        if not task_outputs:
            raise ValueError("No task outputs found in crew result")

        # Process individual task outputs (assuming order: requirements, evaluation)
        if len(task_outputs) < 2:
            raise ValueError(f"Expected at least 2 task outputs, got {len(task_outputs)}")

        # First task: requirements matching
        first_task_output = str(task_outputs[0])
        match_results = extract_match_results(first_task_output)

        # Extract application info from first task output (generated by tool)
        # This will raise ValueError if required fields are missing
        app_info = extract_application_info(first_task_output)

        # Second task: resume evaluation
        second_task_output = str(task_outputs[1])
        eval_data = extract_evaluation_data(second_task_output)
        
        # Check if second task output has match_results (it might include them)
        second_task_parsed = parse_json_from_text(second_task_output)
        if second_task_parsed and isinstance(second_task_parsed, dict) and "match_results" in second_task_parsed:
            # Use match_results from second task if available (more complete)
            match_results = second_task_parsed["match_results"]

        # Combine all data - application info from first task, evaluation data from second task
        screening_result = {
            "application_id": app_info["application_id"],
            "candidate_name": app_info["candidate_name"],
            "job_title": app_info["job_title"],
            "match_results": match_results,
            **eval_data,
        }

        # Validate against ScreeningResult schema - strict validation, no fallbacks
        validated = ScreeningResult(**screening_result)
        return validated.model_dump()

    except Exception as e:
        # Re-raise exception to make failures visible
        raise ValueError(f"Error parsing crew result: {e}") from e
