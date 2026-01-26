"""Reporting pipeline - deterministic report generation."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.reporting.nodes import generate_hr_report


def create_pipeline() -> Pipeline:
    """Create reporting pipeline for generating HR reports."""
    return Pipeline(
        [
            # Generate HR report
            node(
                func=generate_hr_report,
                inputs="screening_result",
                outputs="hr_report",
                name="generate_hr_report",
            ),
        ]
    )
