"""Agent tools for CrewAI agents in screening pipeline.

Tool builder functions for llm_context_node.
These functions take datasets as inputs and return tool objects.

Following CrewAI tool conventions from:
https://docs.crewai.com/en/learn/create-custom-tools
"""

from typing import Any

from crewai.tools import tool

from hr_recruiting.base.utils import get_model_dump
from hr_recruiting.pipelines.screening.helper import (
    match_requirements_to_snippets,
)
from hr_recruiting.pipelines.screening.models import (
    RequirementsMatchingMetadata,
    RequirementsMatchingResult,
    ScoringResult,
)

def build_requirements_matcher_tool(
    application: dict[str, Any],
    job_requirements: dict[str, Any],
    matching_config: dict[str, Any],
) -> Any:
    """Build requirements matcher tool from datasets.

    Args:
        application: Application object with application_id, candidate_id, candidate_name, 
                     evidence_snippets, and artifacts (containing job_id, job_title, location)
        job_requirements: Job requirements data with job_id and requirements
        matching_config: Matching configuration with parameters

    Returns:
        CrewAI tool object
    """

    # Extract IDs and names from Application object
    application_id = application["application_id"]
    candidate_name = application["candidate_name"]
    artifacts = application["artifacts"]
    job_title = artifacts["job_title"]
    snippets_list = application["evidence_snippets"]

    # Extract matching parameters from config
    min_word_length = matching_config.get("min_word_length", 3)
    confidence_config = matching_config.get("confidence", {})

    must_have_conf = confidence_config.get("must_have", {})
    must_have_base = must_have_conf.get("base", 0.5)
    must_have_increment = must_have_conf.get("increment", 0.1)
    must_have_max = must_have_conf.get("max", 0.9)

    nice_to_have_conf = confidence_config.get("nice_to_have", {})
    nice_to_have_base = nice_to_have_conf.get("base", 0.4)
    nice_to_have_increment = nice_to_have_conf.get("increment", 0.1)
    nice_to_have_max = nice_to_have_conf.get("max", 0.8)

    # Get stop words and technical terms from config
    stop_words_list = matching_config.get("stop_words", [])
    stop_words = set(word.lower() for word in stop_words_list)

    technical_terms_list = matching_config.get("technical_terms", [])
    technical_terms = set(term.lower() for term in technical_terms_list)

    @tool("Requirements Matcher")
    def requirements_matcher_tool() -> dict[str, Any]:
        """Match job requirements to evidence snippets from candidate profile.

        This tool performs evidence-based matching of job must-have and nice-to-have
        requirements to candidate evidence snippets. It uses improved matching logic:
        - Filters out stop words
        - Requires at least 2 meaningful keyword matches (or 1 technical term)
        - Prioritizes technical terms over common words

        Returns:
            RequirementsMatchingResult dictionary containing:
            - application_id: Application identifier
            - candidate_name: Candidate name
            - job_title: Job title
            - match_results: List of match results with requirement, requirement_type, snippet_ids, and confidence
            - metadata: Dictionary with total_must_have_requirements and total_nice_to_have_requirements
        """
        must_have = job_requirements.get("must_have", [])
        nice_to_have = job_requirements.get("nice_to_have", [])

        # Match must-have requirements
        must_have_matches = match_requirements_to_snippets(
            requirements=must_have,
            requirement_type="must_have",
            snippets_list=snippets_list,
            min_word_length=min_word_length,
            stop_words=stop_words,
            technical_terms=technical_terms,
            confidence_base=must_have_base,
            confidence_increment=must_have_increment,
            confidence_max=must_have_max,
        )

        # Match nice-to-have requirements
        nice_to_have_matches = match_requirements_to_snippets(
            requirements=nice_to_have,
            requirement_type="nice_to_have",
            snippets_list=snippets_list,
            min_word_length=min_word_length,
            stop_words=stop_words,
            technical_terms=technical_terms,
            confidence_base=nice_to_have_base,
            confidence_increment=nice_to_have_increment,
            confidence_max=nice_to_have_max,
        )

        matches = must_have_matches + nice_to_have_matches

        return get_model_dump(
            RequirementsMatchingResult,
            application_id=application_id,
            candidate_name=candidate_name,
            job_title=job_title,
            match_results=matches,
            metadata=get_model_dump(
                RequirementsMatchingMetadata,
                total_must_have_requirements=len(must_have),
                total_nice_to_have_requirements=len(nice_to_have),
            ),
        )

    return requirements_matcher_tool


def build_scoring_tool(
    scoring_config: dict[str, Any],
) -> Any:
    """Build scoring tool from datasets.

    Args:
        scoring_config: Scoring configuration with weights and bounds

    Returns:
        CrewAI tool object
    """
    # Extract weights and bounds from config
    weights = scoring_config.get("weights", {})
    weight_must_have = weights.get("must_have_coverage", 0.7)
    weight_confidence = weights.get("avg_confidence", 0.3)

    bounds = scoring_config.get("bounds", {})
    match_score_bounds = bounds.get("match_score", {"min": 0.0, "max": 100.0})
    coverage_bounds = bounds.get("must_have_coverage", {"min": 0.0, "max": 1.0})

    @tool("Scoring Tool")
    def scoring_tool(
        match_results_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate weighted match score based on requirement matches.

        This tool calculates the overall match score and must-have coverage based on
        match results from the Requirements Matcher. The match_results_data should
        include both the match_results list and metadata with total requirement counts.

        Args:
            match_results_data: Dictionary from requirements_matcher tool output containing:
                - match_results: List of match results (each with requirement, requirement_type, snippet_ids, confidence)
                - metadata: Dictionary with total_must_have_requirements and total_nice_to_have_requirements

        Returns:
            Dictionary with match_score (0-100), must_have_coverage (0-1), and breakdown
        """
        # Extract match_results and metadata
        match_results = match_results_data.get("match_results", [])
        metadata = match_results_data.get("metadata", {})
        total_must_have_count = metadata.get("total_must_have_requirements", 0)

        # Filter must-have matches using requirement_type field
        must_have_matches = [
            m for m in match_results
            if m.get("requirement_type") == "must_have"
        ]

        must_have_coverage = (
            len(must_have_matches) / total_must_have_count
            if total_must_have_count > 0 else 0.0
        )

        # Calculate overall match score using configurable weights
        # avg_confidence includes ALL matches (both must-have and nice-to-have)
        avg_confidence = (
            sum(m.get("confidence", 0.0) for m in match_results) / len(match_results)
            if match_results else 0.0
        )

        # Weighted formula: 70% must-have coverage, 30% average confidence
        match_score = (must_have_coverage * weight_must_have + avg_confidence * weight_confidence) * 100

        # Round to 2 decimal places
        match_score_rounded = round(min(match_score_bounds["max"], max(match_score_bounds["min"], match_score)), 2)
        must_have_coverage_rounded = round(min(coverage_bounds["max"], max(coverage_bounds["min"], must_have_coverage)), 2)

        return get_model_dump(
            ScoringResult,
            match_score=match_score_rounded,
            must_have_coverage=must_have_coverage_rounded,
            must_have_matches=len(must_have_matches),
            total_matches=len(match_results),
        )

    return scoring_tool
