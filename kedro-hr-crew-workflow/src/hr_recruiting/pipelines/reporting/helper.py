"""Helper functions for reporting pipeline.

This module contains helper functions used by the reporting pipeline nodes
for document generation and formatting.
"""

import re
from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from hr_recruiting.pipelines.screening.models import ScreeningResult


def setup_document(result: ScreeningResult) -> Document:
    """Create and configure the Word document."""
    doc = Document()
    doc.core_properties.title = f"Screening Report - {result.application_id}"
    doc.core_properties.subject = "HR Candidate Screening Report"
    doc.core_properties.author = "HR Recruiting System"
    return doc


def add_header(doc: Document, application_id: str) -> None:
    """Add document header with title and application ID."""
    title = doc.add_heading("Candidate Screening Report", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Application ID: {application_id}")
    doc.add_paragraph("")


def add_summary_table(doc: Document, result: ScreeningResult) -> None:
    """Add executive summary table."""
    doc.add_heading("Executive Summary", level=1)
    summary_table = doc.add_table(rows=4, cols=2)
    summary_table.style = "Light Grid Accent 1"
    
    status_emoji = {
        "proceed": "✅ Proceed",
        "review": "⚠️ Review",
        "reject": "❌ Reject",
    }
    
    summary_data = [
        ("Match Score", f"{result.match_score:.1f}/100"),
        ("Recommendation", result.recommendation.upper()),
        ("Must-Have Coverage", f"{result.must_have_coverage:.0%}"),
        ("Status", status_emoji.get(result.recommendation, "❓ Unknown")),
    ]
    
    for i, (label, value) in enumerate(summary_data):
        label_cell = summary_table.rows[i].cells[0]
        value_cell = summary_table.rows[i].cells[1]
        label_cell.text = label
        value_cell.text = value
        label_cell.paragraphs[0].runs[0].bold = True
    
    doc.add_paragraph("")


def add_bullet_list_section(
    doc: Document,
    heading: str,
    items: list[str],
    prefix: str = "•",
) -> None:
    """Add a section with heading and bullet list."""
    if not items:
        return
    
    doc.add_heading(heading, level=1)
    for item in items:
        # Strip any existing bullets/whitespace from the item
        # Remove common bullet characters and whitespace from the start
        clean_item = item.strip()
        # Remove bullet characters (•, -, *, and various Unicode bullets) from the start
        clean_item = re.sub(r'^[\s•\-\*\u2022\u2023\u2043\u204C\u204D\u2219]+', '', clean_item).strip()
        
        # If prefix is a bullet character, don't add it (List Bullet style adds its own)
        # For other prefixes (like emojis), add them before the item
        if prefix == "•":
            doc.add_paragraph(clean_item, style="List Bullet")
        else:
            doc.add_paragraph(f"{prefix} {clean_item}", style="List Bullet")
    doc.add_paragraph("")


def add_match_results_table(doc: Document, match_results: list[Any]) -> None:
    """Add detailed match results table."""
    if not match_results:
        return
    
    doc.add_heading("Detailed Requirement Matches", level=1)
    match_table = doc.add_table(rows=len(match_results) + 1, cols=3)
    match_table.style = "Light Grid Accent 1"
    
    # Header row
    headers = ["Requirement", "Confidence", "Evidence Count"]
    header_cells = match_table.rows[0].cells
    for i, header_text in enumerate(headers):
        header_cells[i].text = header_text
        header_cells[i].paragraphs[0].runs[0].bold = True
    
    # Data rows
    for i, match in enumerate(match_results, start=1):
        row_cells = match_table.rows[i].cells
        row_cells[0].text = match.requirement
        row_cells[1].text = f"{match.confidence:.0%}"
        row_cells[2].text = str(len(match.snippet_ids))
    
    doc.add_paragraph("")


def add_email_draft_section(doc: Document, email_draft: Any) -> None:
    """Add email draft section."""
    if not email_draft:
        return
    
    doc.add_heading("Drafted Communication", level=1)
    doc.add_paragraph(f"Subject: {email_draft.subject}")
    doc.add_paragraph("")
    doc.add_paragraph("Body:")
    doc.add_paragraph(email_draft.body)
    doc.add_paragraph("")


def add_footer(doc: Document) -> None:
    """Add document footer."""
    doc.add_paragraph("─" * 50)
    doc.add_paragraph("This report was generated automatically by the HR Recruiting System.")
    doc.add_paragraph("Please review all recommendations before taking action.")
