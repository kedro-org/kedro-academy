"""Reporting pipeline - deterministic email drafting and report generation."""

from kedro.pipeline import Pipeline, node

from hr_recruiting.pipelines.reporting.nodes import (
    create_email_draft,
    generate_hr_report,
)


def create_pipeline() -> Pipeline:
    """Create reporting pipeline for email drafting and HR report generation."""
    return Pipeline(
        [
            # Draft email communication (deterministic - uses templates)
            node(
                func=create_email_draft,
                inputs=[
                    "screening_result",
                    "email_templates",
                ],
                outputs="email_draft",
                name="create_email_draft",
            ),
            # Generate HR report
            node(
                func=generate_hr_report,
                inputs=[
                    "screening_result",
                    "email_draft",
                ],
                outputs="hr_report",
                name="generate_hr_report",
            ),
        ]
    )
