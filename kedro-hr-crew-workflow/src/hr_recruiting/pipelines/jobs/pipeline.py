"""Jobs pipeline - deterministic processing of job postings."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.jobs.nodes import (
    normalize_job_posting,
    parse_job_description,
)


def create_pipeline() -> Pipeline:
    """Create the jobs pipeline.

    This pipeline handles deterministic processing of job postings:
    1. Parse raw job posting document
    2. Normalize to structured job posting format

    Returns:
        Configured Pipeline object
    """
    return Pipeline(
        [
            # Parse raw job posting
            node(
                func=parse_job_description,
                inputs="raw_job_posting",
                outputs="parsed_job_description",
                name="parse_job_description",
            ),
            # Normalize to structured format
            node(
                func=normalize_job_posting,
                inputs="parsed_job_description",
                outputs="normalized_job_posting",
                name="normalize_job_posting",
            ),
        ]
    )
