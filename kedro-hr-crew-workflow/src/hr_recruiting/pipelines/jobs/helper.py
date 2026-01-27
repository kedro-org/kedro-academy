"""Helper functions for jobs pipeline.

This module contains helper functions used by the jobs pipeline nodes
for job posting parsing and normalization.
"""

from typing import Any

from hr_recruiting.pipelines.jobs.models import JobMetadata, JobRequirements


def create_job_metadata(
    job_id: str,
    title: str,
    location: str,
) -> dict[str, Any]:
    """Create JobMetadata model from structured data.

    Args:
        job_id: Unique job identifier
        title: Job title
        location: Job location

    Returns:
        JobMetadata dictionary (validated model dumped to dict)

    Raises:
        ValueError: If validation fails
    """
    try:
        job_metadata = JobMetadata(
            job_id=job_id,
            title=title,
            location=location,
        )
        return job_metadata.model_dump()
    except Exception as e:
        raise ValueError(f"Job metadata validation failed: {e}") from e


def create_job_requirements(
    job_id: str,
    must_have: list[str],
    nice_to_have: list[str],
) -> dict[str, Any]:
    """Create JobRequirements model from structured data.

    Args:
        job_id: Unique job identifier
        must_have: List of must-have requirements
        nice_to_have: List of nice-to-have requirements

    Returns:
        JobRequirements dictionary (validated model dumped to dict)

    Raises:
        ValueError: If validation fails
    """
    try:
        job_requirements = JobRequirements(
            job_id=job_id,
            must_have=must_have,
            nice_to_have=nice_to_have,
        )
        return job_requirements.model_dump()
    except Exception as e:
        raise ValueError(f"Job requirements validation failed: {e}") from e


def parse_job_fields(lines: list[str]) -> dict[str, Any]:
    """Parse all job posting fields in a single pass through the lines.

    This function efficiently extracts title, location, and requirements
    by iterating through the lines only once.

    Args:
        lines: List of text lines from the job posting

    Returns:
        Dictionary containing title, location, must_have, and nice_to_have
    """
    title = "Unknown Position"
    location = "Remote"
    must_have: list[str] = []
    nice_to_have: list[str] = []
    
    # Section markers
    MUST_HAVE_MARKERS = ("Must-Have Requirements", "Must Have Requirements")
    NICE_TO_HAVE_MARKERS = ("Nice-to-Have Requirements", "Nice To Have Requirements")
    END_MARKERS = ("Compensation", "Benefits")
    
    title_found = False
    location_found = False
    current_section: str | None = None
    
    for line in lines:
        line_stripped = line.strip()
        
        # Skip empty lines (except for title extraction)
        if not line_stripped:
            continue
        
        # Extract title (first non-empty line)
        if not title_found:
            title = line_stripped
            title_found = True
        
        # Extract location
        if not location_found and line_stripped.startswith("Location:"):
            location = line_stripped.replace("Location:", "", 1).strip()
            location_found = True
        
        # Check for section start markers
        if any(marker in line_stripped for marker in MUST_HAVE_MARKERS):
            current_section = "must_have"
            continue
        
        if any(marker in line_stripped for marker in NICE_TO_HAVE_MARKERS):
            current_section = "nice_to_have"
            continue
        
        # Check for section end markers
        if any(marker in line_stripped for marker in END_MARKERS):
            if current_section == "must_have":
                current_section = None
            elif current_section == "nice_to_have":
                break
        
        # Add to appropriate section
        if current_section == "must_have":
            must_have.append(line_stripped)
        elif current_section == "nice_to_have":
            nice_to_have.append(line_stripped)
    
    return {
        "title": title,
        "location": location,
        "must_have": must_have,
        "nice_to_have": nice_to_have,
    }
