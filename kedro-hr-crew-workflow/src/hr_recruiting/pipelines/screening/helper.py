"""Helper functions for screening pipeline.

This module contains helper functions used by the screening pipeline nodes
for crew orchestration, task creation, and result extraction.
"""

import json
from typing import Any

from kedro.pipeline.llm_context import LLMContext
from pydantic import BaseModel

from hr_recruiting.base.utils import (
    extract_field_from_prompt,
    extract_task_outputs_from_crew_result,
    get_model_dump,
    parse_json_from_text,
)
from hr_recruiting.pipelines.screening.models import ScreeningResult, ScoringResult


def extract_meaningful_keywords(
    text: str,
    min_word_length: int,
    stop_words: set[str],
) -> list[str]:
    """Extract meaningful keywords from text, filtering stop words.

    Args:
        text: Input text to extract keywords from
        min_word_length: Minimum word length to consider
        stop_words: Set of stop words to filter out

    Returns:
        List of meaningful keywords
    """
    # Split into words, lowercase, remove punctuation
    words = [word.lower().strip('.,!?;:()[]{}"\'') for word in text.split()]
    # Filter: min length, not stop word, and meaningful
    keywords = [
        word for word in words
        if len(word) > min_word_length
        and word not in stop_words
        and word.isalnum()  # Only alphanumeric
    ]
    return keywords


def match_requirements_to_snippets(
    requirements: list[str],
    requirement_type: str,
    snippets_list: list[dict[str, Any]],
    min_word_length: int,
    stop_words: set[str],
    technical_terms: set[str],
    confidence_base: float,
    confidence_increment: float,
    confidence_max: float,
) -> list[dict[str, Any]]:
    """Match requirements to evidence snippets.

    Args:
        requirements: List of requirement strings to match
        requirement_type: Type of requirement ("must_have" or "nice_to_have")
        snippets_list: List of evidence snippet dictionaries
        min_word_length: Minimum word length for keywords
        stop_words: Set of stop words to filter
        technical_terms: Set of technical terms to prioritize
        confidence_base: Base confidence score
        confidence_increment: Confidence increment per matching snippet
        confidence_max: Maximum confidence score

    Returns:
        List of match result dictionaries
    """
    matches: list[dict[str, Any]] = []

    for req in requirements:
        matching_snippets = []
        req_keywords = extract_meaningful_keywords(req, min_word_length, stop_words)

        if not req_keywords:  # Skip if no meaningful keywords
            continue

        for snippet in snippets_list:
            snippet_text = snippet.get("text", "")
            snippet_keywords = extract_meaningful_keywords(snippet_text, min_word_length, stop_words)

            # Calculate match score
            match_score = calculate_match_score(req_keywords, snippet_keywords, technical_terms)

            # Only consider it a match if score is above threshold
            if match_score > 0.0:
                matching_snippets.append(snippet.get("snippet_id"))

        if matching_snippets:
            # Confidence based on number of matching snippets and match quality
            confidence = min(
                confidence_max,
                confidence_base + len(matching_snippets) * confidence_increment
            )
            matches.append({
                "requirement": req,
                "requirement_type": requirement_type,
                "snippet_ids": matching_snippets,
                "confidence": confidence,
            })

    return matches


def calculate_match_score(
    req_keywords: list[str],
    snippet_keywords: list[str],
    technical_terms: set[str],
) -> float:
    """Calculate match score based on keyword overlap, prioritizing technical terms.

    Args:
        req_keywords: Keywords from requirement
        snippet_keywords: Keywords from snippet
        technical_terms: Set of technical terms to prioritize

    Returns:
        Match score (0.0 to 1.0)
    """
    if not req_keywords:
        return 0.0

    # Count matches, with higher weight for technical terms
    matches = 0
    technical_matches = 0

    snippet_keywords_set = set(snippet_keywords)
    for keyword in req_keywords:
        if keyword in snippet_keywords_set:
            matches += 1
            if keyword in technical_terms:
                technical_matches += 1

    # Require at least 2 matches (or 1 technical term match)
    if matches < 2 and technical_matches == 0:
        return 0.0

    # Calculate base score: percentage of keywords matched
    base_score = matches / len(req_keywords)

    # Boost score if technical terms matched
    technical_boost = technical_matches * 0.2  # 20% boost per technical match

    return min(1.0, base_score + technical_boost)


def extract_task_fields_from_prompt(
    context: LLMContext,
    prompt_name: str,
    model_class: type[BaseModel],
    format_kwargs: dict[str, Any],
) -> tuple[str, str]:
    """Extract description and expected_output from formatted prompt.

    Args:
        context: LLMContext containing prompts
        prompt_name: Name of the prompt in context
        model_class: Pydantic model class for schema JSON
        format_kwargs: Keyword arguments for formatting the prompt

    Returns:
        Tuple of (description, expected_output)

    Raises:
        ValueError: If prompt is missing or fields cannot be extracted
    """
    # Get schema JSON from Pydantic model
    schema_json = json.dumps(model_class.model_json_schema(), indent=2)

    # Format prompt with schema JSON and provided kwargs
    # All prompts use "output_schema" as the fixed placeholder name
    user_prompt = context.prompts.get(prompt_name)
    if not user_prompt:
        raise ValueError(f"{prompt_name} not found in context")

    try:
        formatted = user_prompt.format(
            **format_kwargs,
            output_schema=schema_json,
        )
        # Extract the string content properly
        if isinstance(formatted, list) and formatted:
            prompt_content = str(
                formatted[-1].content if hasattr(formatted[-1], "content") else formatted[-1]
            )
        else:
            prompt_content = str(formatted)

        # Strip leading/trailing whitespace
        prompt_content = prompt_content.strip()
    except Exception as e:
        raise ValueError(f"Error formatting {prompt_name}: {e}") from e

    description = extract_field_from_prompt(prompt_content, "description")
    if not description:
        raise ValueError(
            f"description not found in {prompt_name}. Prompt content preview: {prompt_content[:200]}"
        )

    expected_output = extract_field_from_prompt(prompt_content, "expected_output")
    if not expected_output:
        raise ValueError(f"expected_output not found in {prompt_name}")

    return description, expected_output


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
    
    
    CTXInputs[LLM + Prompts] --> CTX2[Resume Evaluator Context]
    SCORE[Deterministic Scoring]
    AGENT1OUTPUT --> SCORE
    SCORE --> AGENT2[ResumeEvaluatorAgent + ResumeEvaluationTask]
    CTX2 --> AGENT2
    AGENT2OUTPUT[EvaluationResults]
    AGENT2 --> AGENT2OUTPUT
    
    AGENT2OUTPUT --> OUTPUT[ScreeningResult]
    
    style CTX1 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style CTX2 fill:#4A90E2,stroke:#2E5C8A,stroke-width:2px,color:#fff
    style AGENT1 fill:#50C878,stroke:#2D8659,stroke-width:2px,color:#fff
    style AGENT2 fill:#50C878,stroke:#2D8659,stroke-width:2px,color:#fff
    style OUTPUT fill:#6C5CE7,stroke:#4A3FA8,stroke-width:2px,color:#fff"""


def calculate_scoring_result(
    match_results_data: dict[str, Any],
    scoring_config: dict[str, Any],
) -> dict[str, Any]:
    """Calculate weighted match score from requirements matching output.

    Args:
        match_results_data: RequirementsMatchingResult-style dict with match_results
            and metadata.total_must_have_requirements
        scoring_config: Scoring weights and bounds from catalog

    Returns:
        ScoringResult dictionary
    """
    match_results = match_results_data.get("match_results", [])
    metadata = match_results_data.get("metadata", {})
    total_must_have_count = metadata.get("total_must_have_requirements", 0)

    must_have_matches = [
        match for match in match_results
        if match.get("requirement_type") == "must_have"
    ]

    must_have_coverage = (
        len(must_have_matches) / total_must_have_count
        if total_must_have_count > 0 else 0.0
    )

    avg_confidence = (
        sum(match.get("confidence", 0.0) for match in match_results) / len(match_results)
        if match_results else 0.0
    )

    weights = scoring_config.get("weights", {})
    weight_must_have = weights.get("must_have_coverage", 0.7)
    weight_confidence = weights.get("avg_confidence", 0.3)

    bounds = scoring_config.get("bounds", {})
    match_score_bounds = bounds.get("match_score", {"min": 0.0, "max": 100.0})
    coverage_bounds = bounds.get("must_have_coverage", {"min": 0.0, "max": 1.0})

    match_score = (
        must_have_coverage * weight_must_have + avg_confidence * weight_confidence
    ) * 100

    return get_model_dump(
        ScoringResult,
        match_score=round(
            min(match_score_bounds["max"], max(match_score_bounds["min"], match_score)),
            2,
        ),
        must_have_coverage=round(
            min(coverage_bounds["max"], max(coverage_bounds["min"], must_have_coverage)),
            2,
        ),
        must_have_matches=len(must_have_matches),
        total_matches=len(match_results),
    )


def _extract_single_task_output(
    task_output: Any,
    model_class: type[BaseModel],
) -> dict[str, Any]:
    """Extract structured output from a single CrewAI task output."""
    if hasattr(task_output, "pydantic") and task_output.pydantic is not None:
        return get_model_dump(
            model_class,
            **task_output.pydantic.model_dump(mode="json"),
        )

    parsed = parse_json_from_text(str(task_output))
    if not parsed or not isinstance(parsed, dict):
        raise ValueError(
            f"Failed to parse structured output from task result: {str(task_output)[:200]}"
        )

    return get_model_dump(model_class, **parsed)


def apply_recommendation_guardrails(
    llm_recommendation: str,
    match_score: float,
    must_have_coverage: float,
    match_results: list[dict[str, Any]],
    total_must_have_requirements: int,
) -> str:
    """Enforce proceed/review/reject thresholds from the evaluator prompt.

    The LLM proposes a recommendation and narrative; this function ensures the
    final label matches the hard rules defined in resume_evaluation_user_prompt.yml.
    """
    must_have_matches = [
        match for match in match_results
        if match.get("requirement_type") == "must_have"
    ]

    if match_score < 70 or must_have_coverage < 0.70:
        return "reject"

    low_confidence_must_haves = [
        match for match in must_have_matches
        if match.get("confidence", 0.0) < 0.5
    ]
    if len(low_confidence_must_haves) >= 2:
        return "reject"

    all_must_haves_matched = len(must_have_matches) == total_must_have_requirements
    all_matched_confident = all(
        match.get("confidence", 0.0) >= 0.6 for match in must_have_matches
    )
    meets_proceed = (
        match_score >= 80
        and must_have_coverage >= 0.85
        and all_must_haves_matched
        and all_matched_confident
    )

    if meets_proceed:
        return "proceed"

    # Passed minimum bar but did not meet proceed criteria — never reject here.
    if llm_recommendation == "proceed":
        return "review"

    return "review"


def merge_screening_result(
    matching_result: dict[str, Any],
    scoring_result: dict[str, Any],
    evaluation_result: dict[str, Any],
) -> dict[str, Any]:
    """Combine deterministic matching/scoring with LLM evaluation."""
    total_must_have = matching_result["metadata"]["total_must_have_requirements"]
    recommendation = apply_recommendation_guardrails(
        llm_recommendation=evaluation_result["recommendation"],
        match_score=scoring_result["match_score"],
        must_have_coverage=scoring_result["must_have_coverage"],
        match_results=matching_result["match_results"],
        total_must_have_requirements=total_must_have,
    )
    return get_model_dump(
        ScreeningResult,
        application_id=matching_result["application_id"],
        candidate_name=matching_result["candidate_name"],
        job_title=matching_result["job_title"],
        match_score=scoring_result["match_score"],
        must_have_coverage=scoring_result["must_have_coverage"],
        match_results=matching_result["match_results"],
        gaps=evaluation_result.get("gaps", []),
        strengths=evaluation_result.get("strengths", []),
        risk_flags=evaluation_result.get("risk_flags", []),
        recommendation=recommendation,
        qa_suggestions=(
            [] if recommendation == "reject"
            else evaluation_result.get("qa_suggestions", [])
        ),
    )
