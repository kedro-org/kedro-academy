"""Jobs pipeline nodes - deterministic functions."""

from typing import Any

from hr_recruiting.base.utils import get_model_dump, extract_text_from_document
from hr_recruiting.pipelines.jobs.helper import parse_job_fields
from hr_recruiting.pipelines.jobs.models import JobMetadata, JobRequirements, ParsedJobPosting


def parse_job_posting(raw_job_doc: Any) -> dict[str, Any]:
    """Parse raw job posting Word document and extract all fields.
    
    Returns:
        ParsedJobPosting model dumped to dict for Kedro dataset compatibility
    
    Raises:
        ValueError: If job_id cannot be extracted from document properties
    """
    # Extract all text from the document
    raw_text = extract_text_from_document(raw_job_doc)
    
    # Try to extract job_id from document properties
    job_id = None
    if hasattr(raw_job_doc.core_properties, "title") and raw_job_doc.core_properties.title:
        job_id = raw_job_doc.core_properties.title
    elif hasattr(raw_job_doc.core_properties, "subject") and raw_job_doc.core_properties.subject:
        job_id = raw_job_doc.core_properties.subject
    
    if not job_id:
        raise ValueError("job_id not found in job document properties (title or subject)")
    
    # Parse all fields from the raw text
    lines = raw_text.split("\n")
    parsed_fields = parse_job_fields(lines)
    
    # Create and validate ParsedJobPosting model using utility function
    return get_model_dump(
        ParsedJobPosting,
        job_id=job_id,
        raw_jd_text=raw_text,
        title=parsed_fields["title"],
        location=parsed_fields["location"],
        must_have=parsed_fields["must_have"],
        nice_to_have=parsed_fields["nice_to_have"],
    )


def split_job_posting(parsed_jd: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split parsed job posting into metadata and requirements.
    
    This function simply splits the already-parsed job posting data into
    JobMetadata (for applications pipeline) and JobRequirements (for screening pipeline).

    Args:
        parsed_jd: ParsedJobPosting model dictionary

    Returns:
        Tuple of (job_metadata, job_requirements) dictionaries
    """
    # Create JobMetadata for applications pipeline 
    # to generate application id from job_id and candidate_id
    job_metadata = get_model_dump(
        JobMetadata,
        job_id=parsed_jd["job_id"],
        title=parsed_jd["title"],
        location=parsed_jd["location"],
    )
    
    # Create JobRequirements for screening pipeline
    job_requirements = get_model_dump(
        JobRequirements,
        job_id=parsed_jd["job_id"],
        must_have=parsed_jd["must_have"],
        nice_to_have=parsed_jd["nice_to_have"],
    )
    
    return job_metadata, job_requirements