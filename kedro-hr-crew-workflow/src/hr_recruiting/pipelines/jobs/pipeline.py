"""Jobs pipeline - deterministic processing of job postings."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.jobs.nodes import (
    parse_job_description,
    split_job_posting,
)


def create_pipeline() -> Pipeline:
    """Create jobs pipeline for processing job postings."""
    return Pipeline(
        [
            # Parse raw job posting
            node(
                func=parse_job_description,
                inputs="raw_job_posting",
                outputs="parsed_job_description",
                name="parse_job_description",
            ),
            # Split into metadata and requirements
            node(
                func=split_job_posting,
                inputs="parsed_job_description",
                outputs=["job_metadata", "job_requirements"],
                name="split_job_posting",
            ),
        ]
    )
