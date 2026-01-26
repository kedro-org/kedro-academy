"""Jobs pipeline nodes - deterministic functions."""

from typing import Any

from hr_recruiting.base.utils import extract_text_from_document
from hr_recruiting.pipelines.jobs.helper import (
    parse_job_fields,
    validate_job_posting,
)


def parse_job_description(raw_job_doc: Any) -> dict[str, Any]:
    """Parse raw job posting Word document.

    This is a deterministic function that extracts text from a Word document.
    Uses python-docx to parse .docx files.

    Args:
        raw_job_doc: python-docx Document object containing job posting

    Returns:
        Parsed job description with extracted text
    """
    # Extract all text from the document
    raw_text = extract_text_from_document(raw_job_doc)
    
    # Try to extract job_id from document properties or filename
    # In production, this might come from document properties or metadata
    job_id = "unknown"
    if hasattr(raw_job_doc.core_properties, "title") and raw_job_doc.core_properties.title:
        job_id = raw_job_doc.core_properties.title
    elif hasattr(raw_job_doc.core_properties, "subject") and raw_job_doc.core_properties.subject:
        job_id = raw_job_doc.core_properties.subject

    return {
        "job_id": job_id,
        "raw_jd_text": raw_text,
        "metadata": {
            "author": raw_job_doc.core_properties.author if hasattr(raw_job_doc.core_properties, "author") else "",
            "created": str(raw_job_doc.core_properties.created) if hasattr(raw_job_doc.core_properties, "created") else "",
        },
    }


def normalize_job_posting(parsed_jd: dict[str, Any]) -> dict[str, Any]:
    """Normalize job posting to structured format.

    This is a deterministic node that converts parsed data to JobPosting model.
    The parsed data comes from Word document parsing, which extracts raw text.
    This function parses the raw text to extract structured fields like title,
    location, and requirements in a single efficient pass.

    Args:
        parsed_jd: Parsed job description data from Word document

    Returns:
        Normalized job posting as dictionary
    """
    raw_text = parsed_jd.get("raw_jd_text", "")
    lines = raw_text.split("\n")
    
    # Extract all fields
    parsed_fields = parse_job_fields(lines)
    
    job_data = {
        "job_id": parsed_jd.get("job_id", "unknown"),
        "title": parsed_fields["title"],
        "location": parsed_fields["location"],
        "requirements": {
            "must_have": parsed_fields["must_have"],
            "nice_to_have": parsed_fields["nice_to_have"],
        },
        "raw_jd_text": raw_text,
    }

    # Validate using Pydantic model
    job_posting = validate_job_posting(job_data)
    return job_posting.model_dump()
