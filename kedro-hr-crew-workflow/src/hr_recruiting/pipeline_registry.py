"""Pipeline registry for HR recruiting workflows.

This module registers all pipelines and combines them into logical groups
for execution. The default pipeline runs the complete workflow from job
posting parsing through candidate screening and report generation.
"""

from kedro.pipeline import Pipeline

from hr_recruiting.pipelines.applications import create_pipeline as create_applications_pipeline
from hr_recruiting.pipelines.jobs import create_pipeline as create_jobs_pipeline
from hr_recruiting.pipelines.reporting import create_pipeline as create_reporting_pipeline
from hr_recruiting.pipelines.screening import create_pipeline as create_screening_pipeline


def register_pipelines() -> dict[str, Pipeline]:
    """Register all pipelines for the HR recruiting workflow.
    
    Returns:
        Dictionary of pipeline names to Pipeline instances:
        - "__default__": Complete workflow (jobs + applications + screening + reporting)
        - "hr": HR workflow (applications + screening + reporting)
        - "jobs": Jobs pipeline only
        - "applications": Applications pipeline only
        - "screening": Screening pipeline only
        - "reporting": Reporting pipeline only
    """
    # Individual pipelines
    jobs_pipeline = create_jobs_pipeline()
    applications_pipeline = create_applications_pipeline()
    screening_pipeline = create_screening_pipeline()
    reporting_pipeline = create_reporting_pipeline()

    # Combined HR pipeline: applications + screening + reporting
    hr_pipeline = (
        applications_pipeline
        + screening_pipeline
        + reporting_pipeline
    )

    return {
        "__default__": jobs_pipeline + hr_pipeline,
        "hr": hr_pipeline,
        "jobs": jobs_pipeline,
        "applications": applications_pipeline,
        "screening": screening_pipeline,
        "reporting": reporting_pipeline,
    }
