"""Jobs pipeline nodes - deterministic functions."""

from typing import Any

from hr_recruiting.base.utils import extract_text_from_document
from hr_recruiting.pipelines.jobs.helper import (
    create_job_metadata,
    create_job_requirements,
    parse_job_fields,
)


def parse_job_description(raw_job_doc: Any) -> dict[str, Any]:
    """Parse raw job posting Word document."""
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


def split_job_posting(parsed_jd: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split job posting into metadata and requirements.

    Args:
        parsed_jd: Parsed job description dictionary

    Returns:
        Tuple of (job_metadata, job_requirements) dictionaries
    """
    raw_text = parsed_jd.get("raw_jd_text", "")
    lines = raw_text.split("\n")
    
    # Extract all fields
    parsed_fields = parse_job_fields(lines)
    
    if "job_id" not in parsed_jd:
        raise ValueError("job_id not found in parsed_jd")
    job_id = parsed_jd["job_id"]
    
    # Create JobMetadata for applications pipeline
    job_metadata = create_job_metadata(
        job_id=job_id,
        title=parsed_fields["title"],
        location=parsed_fields["location"],
    )
    
    # Create JobRequirements for screening pipeline
    job_requirements = create_job_requirements(
        job_id=job_id,
        must_have=parsed_fields["must_have"],
        nice_to_have=parsed_fields["nice_to_have"],
    )
    
    return job_metadata, job_requirements