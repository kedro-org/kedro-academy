"""Reporting pipeline nodes - deterministic email drafting and report generation."""

from typing import Any

from docx import Document

from hr_recruiting.pipelines.reporting.helper import (
    add_bullet_list_section,
    add_email_draft_section,
    add_footer,
    add_header,
    add_match_results_table,
    add_summary_table,
    draft_email,
    setup_document,
)
from hr_recruiting.pipelines.reporting.models import EmailDraft
from hr_recruiting.pipelines.screening.models import ScreeningResult


def create_email_draft(
    screening_result: dict[str, Any],
    email_templates: dict[str, Any],
) -> dict[str, Any]:
    """Create email draft using templates.

    Args:
        screening_result: Screening result with candidate_name, job_title, recommendation, and qa_suggestions
        email_templates: Email templates dictionary from config

    Returns:
        EmailDraft dictionary with subject, body, and placeholders
    """
    return draft_email(screening_result, email_templates)


def generate_hr_report(
    screening_result: dict[str, Any],
    email_draft: dict[str, Any],
) -> Document:
    """Generate HR report from screening result and email draft.

    Args:
        screening_result: Screening result from screening pipeline
        email_draft: Email draft from create_email_draft node

    Returns:
        Word document with complete HR report
    """
    # Validate screening result
    result = ScreeningResult(**screening_result)

    # Validate email draft
    email = EmailDraft(**email_draft)

    # Setup document
    doc = setup_document(result)

    # Add header
    add_header(doc, result.application_id)

    # Add executive summary
    add_summary_table(doc, result)

    # Add candidate strengths
    add_bullet_list_section(doc, "Candidate Strengths", result.strengths)

    # Add identified gaps
    add_bullet_list_section(doc, "Identified Gaps", result.gaps)

    # Add risk flags
    add_bullet_list_section(doc, "Risk Flags", result.risk_flags, prefix="⚠️")

    # Add detailed match results
    add_match_results_table(doc, result.match_results)

    # Add email draft
    add_email_draft_section(doc, email)

    # Add QA suggestions
    add_bullet_list_section(doc, "Next Steps / QA Suggestions", result.qa_suggestions)

    # Add footer
    add_footer(doc)

    return doc
