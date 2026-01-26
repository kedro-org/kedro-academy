"""Reporting pipeline nodes - deterministic functions."""

from typing import Any

from docx import Document

from hr_recruiting.pipelines.reporting.helper import (
    add_bullet_list_section,
    add_email_draft_section,
    add_footer,
    add_header,
    add_match_results_table,
    add_summary_table,
    setup_document,
)
from hr_recruiting.pipelines.screening.models import ScreeningResult


def generate_hr_report(screening_result: dict[str, Any]) -> Document:
    """Generate HR report from screening result."""
    # Validate and create ScreeningResult model (ensures data structure is correct)
    result = ScreeningResult(**screening_result)

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
    add_email_draft_section(doc, result.email_draft)
    
    # Add QA suggestions
    add_bullet_list_section(doc, "Next Steps / QA Suggestions", result.qa_suggestions)
    
    # Add footer
    add_footer(doc)
    
    return doc
