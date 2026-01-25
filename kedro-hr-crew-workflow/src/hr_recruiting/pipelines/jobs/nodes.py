"""Jobs pipeline nodes - deterministic functions."""

from typing import Any

from hr_recruiting.base.models import JobPosting
from hr_recruiting.base.utils import extract_text_from_document


def validate_job_posting(data: dict[str, Any]) -> JobPosting:
    """Validate and create JobPosting model.

    Args:
        data: Raw job posting data

    Returns:
        Validated JobPosting model

    Raises:
        ValueError: If validation fails
    """
    try:
        return JobPosting(**data)
    except Exception as e:
        raise ValueError(f"Job posting validation failed: {e}") from e


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
    In a production implementation, this would use NLP/LLM to extract structured
    data (title, location, requirements) from the raw text.

    Args:
        parsed_jd: Parsed job description data from Word document

    Returns:
        Normalized job posting as dictionary
    """
    # In a real implementation, this would use NLP/LLM to extract structured data
    # from the raw_jd_text. For now, we create a simple structure with defaults.
    # The raw text is preserved for downstream agentic processing.
    job_data = {
        "job_id": parsed_jd.get("job_id", "unknown"),
        "title": parsed_jd.get("metadata", {}).get("title", "Unknown Position"),
        "location": parsed_jd.get("metadata", {}).get("location", "Remote"),
        "requirements": {
            "must_have": parsed_jd.get("metadata", {}).get("must_have", []),
            "nice_to_have": parsed_jd.get("metadata", {}).get("nice_to_have", []),
        },
        "raw_jd_text": parsed_jd.get("raw_jd_text", ""),
    }

    # Validate using Pydantic model
    job_posting = validate_job_posting(job_data)
    return job_posting.model_dump()
