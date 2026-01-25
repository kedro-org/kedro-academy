"""Reporting pipeline - deterministic report generation."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.reporting.nodes import (
    generate_hr_report,
    validate_screening_result,
)


def create_pipeline() -> Pipeline:
    """Create reporting pipeline.

    This pipeline handles deterministic post-processing:
    1. Validate screening result
    2. Generate HR report

    Returns:
        Configured Pipeline object
    """
    return Pipeline(
        [
            # Validate screening result
            node(
                func=validate_screening_result,
                inputs="screening_result_raw",
                outputs="screening_result",
                name="validate_screening_result",
            ),
            # Generate HR report
            node(
                func=generate_hr_report,
                inputs="screening_result",
                outputs="hr_report",
                name="generate_hr_report",
            ),
        ]
    )
