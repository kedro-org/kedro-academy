"""Applications pipeline - deterministic processing of resumes."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.applications.nodes import (
    extract_evidence_snippets,
    normalize_candidate_profile,
    parse_resume,
)


def create_pipeline() -> Pipeline:
    """Create the applications pipeline.

    This pipeline handles deterministic processing of resumes:
    1. Parse raw resume document
    2. Normalize to structured candidate profile
    3. Extract evidence snippets

    Returns:
        Configured Pipeline object
    """
    return Pipeline(
        [
            # Parse raw resume
            node(
                func=parse_resume,
                inputs="raw_resume",
                outputs="parsed_resume",
                name="parse_resume",
            ),
            # Normalize to structured format
            node(
                func=normalize_candidate_profile,
                inputs="parsed_resume",
                outputs="normalized_candidate_profile",
                name="normalize_candidate_profile",
            ),
            # Extract evidence snippets
            node(
                func=extract_evidence_snippets,
                inputs=[
                    "normalized_candidate_profile",
                    "params:evidence.max_snippet_length",
                ],
                outputs="evidence_snippets",
                name="extract_evidence_snippets",
            ),
        ]
    )
