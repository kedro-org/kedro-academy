"""Pipeline definitions."""

from kedro.pipeline import Pipeline

from .applications import create_pipeline as create_applications_pipeline
from .jobs import create_pipeline as create_jobs_pipeline
from .reporting import create_pipeline as create_reporting_pipeline
from .screening import create_pipeline as create_screening_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register the project's pipelines.

    Returns:
        A mapping from pipeline names to Pipeline objects.
    """
    # Individual pipelines
    jobs_pipeline = create_jobs_pipeline()
    applications_pipeline = create_applications_pipeline()
    screening_pipeline = create_screening_pipeline()
    reporting_pipeline = create_reporting_pipeline()

    # Combined HR pipeline: jobs + applications + screening + reporting
    hr_pipeline = (
        jobs_pipeline
        + applications_pipeline
        + screening_pipeline
        + reporting_pipeline
    )

    return {
        "__default__": hr_pipeline,
        "hr": hr_pipeline,
        "jobs": jobs_pipeline,
        "applications": applications_pipeline,
        "screening": screening_pipeline,
        "reporting": reporting_pipeline,
    }
