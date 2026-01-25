"""Application pipeline nodes - deterministic functions."""

from typing import Any

from hr_recruiting.base.models import CandidateProfile
from hr_recruiting.base.utils import extract_text_from_document


def validate_candidate_profile(data: dict[str, Any]) -> CandidateProfile:
    """Validate and create CandidateProfile model.

    Args:
        data: Raw candidate profile data

    Returns:
        Validated CandidateProfile model

    Raises:
        ValueError: If validation fails
    """
    try:
        return CandidateProfile(**data)
    except Exception as e:
        raise ValueError(f"Candidate profile validation failed: {e}") from e


def parse_resume(raw_resume_doc: Any) -> dict[str, Any]:
    """Parse raw resume Word document.

    Args:
        raw_resume_doc: python-docx Document object containing resume

    Returns:
        Parsed resume with extracted text
    """
    # Extract all text from the document
    raw_text = extract_text_from_document(raw_resume_doc)
    
    # Try to extract candidate_id from document properties
    # In production, this might come from document properties or metadata
    candidate_id = "unknown"
    if hasattr(raw_resume_doc.core_properties, "title") and raw_resume_doc.core_properties.title:
        candidate_id = raw_resume_doc.core_properties.title
    elif hasattr(raw_resume_doc.core_properties, "subject") and raw_resume_doc.core_properties.subject:
        candidate_id = raw_resume_doc.core_properties.subject

    return {
        "candidate_id": candidate_id,
        "raw_resume_text": raw_text,
        "metadata": {
            "author": raw_resume_doc.core_properties.author if hasattr(raw_resume_doc.core_properties, "author") else "",
            "created": str(raw_resume_doc.core_properties.created) if hasattr(raw_resume_doc.core_properties, "created") else "",
        },
    }


def normalize_candidate_profile(parsed_resume: dict[str, Any]) -> dict[str, Any]:
    """Normalize candidate profile to structured format.

    This is a deterministic node that converts parsed data to CandidateProfile model.
    The parsed data comes from Word document parsing, which extracts raw text.
    In a production implementation, this would use NLP/LLM to extract structured
    data (name, email, skills, work history, education) from the raw text.

    Args:
        parsed_resume: Parsed resume data from Word document

    Returns:
        Normalized candidate profile as dictionary
    """
    # In a real implementation, this would use NLP/LLM to extract structured data
    # from the raw_resume_text. For now, we create a simple structure with defaults.
    # The raw text is preserved for downstream agentic processing.
    candidate_data = {
        "candidate_id": parsed_resume.get("candidate_id", "unknown"),
        "name": parsed_resume.get("metadata", {}).get("name", "Unknown"),
        "email": parsed_resume.get("metadata", {}).get("email", "unknown@example.com"),
        "skills": parsed_resume.get("metadata", {}).get("skills", []),
        "work_history": parsed_resume.get("metadata", {}).get("work_history", []),
        "education": parsed_resume.get("metadata", {}).get("education", []),
        "raw_resume_text": parsed_resume.get("raw_resume_text", ""),
    }

    # Validate using Pydantic model
    candidate_profile = validate_candidate_profile(candidate_data)
    return candidate_profile.model_dump()


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length if needed.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def _create_snippet(
    snippet_id: str,
    text: str,
    source: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Create a standardized evidence snippet.

    Args:
        snippet_id: Unique identifier for the snippet
        text: Snippet text content
        source: Source field (e.g., 'skills', 'work_history', 'education')
        metadata: Additional metadata dictionary

    Returns:
        Evidence snippet dictionary
    """
    return {
        "snippet_id": snippet_id,
        "text": text,
        "source": source,
        "metadata": metadata,
    }


def _extract_skill_snippets(
    skills: list[str],
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Extract evidence snippets from skills.

    Args:
        skills: List of skill strings
        start_id: Starting snippet ID counter

    Returns:
        List of skill snippets
    """
    return [
        _create_snippet(
            snippet_id=f"skill_{start_id + idx}",
            text=skill,
            source="skills",
            metadata={"skill": skill},
        )
        for idx, skill in enumerate(skills)
        if skill.strip()  # Skip empty skills
    ]


def _extract_work_history_snippets(
    work_history: list[dict[str, Any]],
    max_snippet_length: int,
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Extract evidence snippets from work history.

    Args:
        work_history: List of work history entries
        max_snippet_length: Maximum length for snippet text
        start_id: Starting snippet ID counter

    Returns:
        List of work history snippets
    """
    snippets = []
    for idx, work in enumerate(work_history):
        role = work.get("role", "").strip()
        company = work.get("company", "").strip()
        description = work.get("description", "").strip()
        
        # Build work text efficiently
        parts = []
        if role:
            parts.append(role)
        if company:
            parts.append(f"at {company}")
        if description:
            parts.append(description)
        
        work_text = ". ".join(parts) if parts else ""
        if not work_text:
            continue  # Skip empty work entries
        
        work_text = _truncate_text(work_text, max_snippet_length)
        
        snippets.append(
            _create_snippet(
                snippet_id=f"work_{start_id + idx}",
                text=work_text,
                source="work_history",
                metadata={
                    "company": company,
                    "role": role,
                },
            )
        )
    return snippets


def _extract_education_snippets(
    education: list[dict[str, Any]],
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Extract evidence snippets from education.

    Args:
        education: List of education entries
        start_id: Starting snippet ID counter

    Returns:
        List of education snippets
    """
    snippets = []
    for idx, edu in enumerate(education):
        degree = edu.get("degree", "").strip()
        field = edu.get("field", "").strip() or "N/A"
        institution = edu.get("institution", "").strip()
        
        # Build education text efficiently
        parts = []
        if degree:
            parts.append(degree)
        if field and field != "N/A":
            parts.append(f"in {field}")
        if institution:
            parts.append(f"from {institution}")
        
        edu_text = " ".join(parts) if parts else ""
        if not edu_text:
            continue  # Skip empty education entries
        
        snippets.append(
            _create_snippet(
                snippet_id=f"edu_{start_id + idx}",
                text=edu_text,
                source="education",
                metadata={
                    "institution": institution,
                    "degree": degree,
                },
            )
        )
    return snippets


def extract_evidence_snippets(
    normalized_candidate_profile: dict[str, Any],
    max_snippet_length: int = 200,
) -> list[dict[str, Any]]:
    """Extract evidence snippets from candidate profile for matching.

    This is a deterministic function that creates snippets from candidate data.
    Extracts from skills, work history, and education.

    Args:
        normalized_candidate_profile: Normalized candidate profile data
        max_snippet_length: Maximum length of each snippet

    Returns:
        List of evidence snippets with IDs
    """
    snippets: list[dict[str, Any]] = []
    snippet_id = 0

    # Extract from skills
    skills = normalized_candidate_profile.get("skills", [])
    if skills:
        skill_snippets = _extract_skill_snippets(skills, start_id=snippet_id + 1)
        snippets.extend(skill_snippets)
        snippet_id += len(skill_snippets)

    # Extract from work history
    work_history = normalized_candidate_profile.get("work_history", [])
    if work_history:
        work_snippets = _extract_work_history_snippets(
            work_history, max_snippet_length, start_id=snippet_id + 1
        )
        snippets.extend(work_snippets)
        snippet_id += len(work_snippets)

    # Extract from education
    education = normalized_candidate_profile.get("education", [])
    if education:
        edu_snippets = _extract_education_snippets(education, start_id=snippet_id + 1)
        snippets.extend(edu_snippets)

    return snippets
