"""Shared utility functions used across pipelines."""

import inspect
import json
import re
import textwrap
import time
from typing import Any, Callable, TypeVar

from crewai import Crew
from docx import Document
from kedro.pipeline.preview_contract import TextPreview
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

def get_document_id(doc: Document, id_name: str = "document_id") -> str:
    """Extract document ID from document properties (title or subject).
    
    Tries to extract an identifier from the document's core properties,
    checking title first, then subject as fallback.
    
    Args:
        doc: python-docx Document object
        id_name: Name of the ID for error messages (e.g., "candidate_id", "job_id")
        
    Returns:
        Document ID string
        
    Raises:
        ValueError: If ID cannot be extracted from document properties
    """
    doc_id = None
    if hasattr(doc.core_properties, "title") and doc.core_properties.title:
        doc_id = doc.core_properties.title
    elif hasattr(doc.core_properties, "subject") and doc.core_properties.subject:
        doc_id = doc.core_properties.subject
    
    if not doc_id:
        raise ValueError(
            f"{id_name} not found in document properties (title or subject)"
        )
    
    return doc_id


def extract_text_from_document(doc: Document) -> str:
    """Extract all text from a Word document.

    Args:
        doc: python-docx Document object

    Returns:
        Extracted text as a single string
    """
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text.strip())
    
    # Also extract text from tables if present
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    text_parts.append(cell.text.strip())
    
    return "\n".join(text_parts)


def parse_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON from text that may contain markdown or other formatting.

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    if not text:
        return None

    # Try to find JSON in code blocks
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find JSON object directly
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try parsing the entire text
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None


def execute_crew_with_retry(
    crew: Crew,
    max_retries: int = 3,
) -> Any:
    """Execute CrewAI crew with retry logic for connection errors.

    Args:
        crew: Configured Crew instance
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Crew execution result

    Raises:
        ConnectionError, ConnectionResetError, OSError: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            return crew.kickoff()
        except (ConnectionError, ConnectionResetError, OSError) as e:
            if attempt < max_retries - 1:
                print(f"Connection error (attempt {attempt + 1}/{max_retries}): {e}. Retrying...")  # noqa: T201
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise


def extract_task_outputs_from_crew_result(crew_result: Any) -> list[Any]:
    """Extract all task outputs from CrewAI crew result.

    Tries multiple ways to access task outputs to handle different
    CrewAI result structures. Returns a list of all task outputs.

    Args:
        crew_result: Result from crew.kickoff()

    Returns:
        List of task outputs (empty list if none found)
    """
    # Try different ways to access task outputs
    if hasattr(crew_result, "tasks_output") and crew_result.tasks_output:
        # Handle both list and single value
        if isinstance(crew_result.tasks_output, list):
            return crew_result.tasks_output
        return [crew_result.tasks_output]
    elif hasattr(crew_result, "tasks") and crew_result.tasks:
        return [task.output for task in crew_result.tasks if hasattr(task, "output")]
    elif isinstance(crew_result, list):
        return crew_result
    elif isinstance(crew_result, str):
        return [crew_result]
    
    return []


def get_model_dump(
    model_class: type[T],
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a Pydantic model instance, validate it, and return as dict.
    
    This utility function eliminates the need for individual create_* functions
    for simple model creation cases where we just need to pass kwargs to the
    model constructor and return the dumped dict.
    
    Args:
        model_class: Pydantic model class to instantiate
        **kwargs: Keyword arguments to pass to model constructor
        
    Returns:
        Validated model dumped to dict (using mode='json' for datetime serialization)
        
    Raises:
        ValueError: If model validation fails
    """
    try:
        model_instance = model_class(**kwargs)
        return model_instance.model_dump(mode="json")
    except Exception as e:
        raise ValueError(
            f"Validation failed for {model_class.__name__}: {e}"
        ) from e


def extract_field_from_prompt(prompt_content: str, field_name: str) -> str | None:
    """Extract a field value from prompt content string.

    The prompt content contains fields like "description: ..." and "expected_output: ..."
    This function extracts the value for a given field. Handles fields that may be
    indented or at the start of lines.

    Args:
        prompt_content: The prompt content string
        field_name: Name of the field to extract (e.g., "description", "expected_output")

    Returns:
        The field value or None if not found
    """
    if not prompt_content:
        return None
    
    # Pattern to match "field_name: value" where field may have leading whitespace
    # and value can span multiple lines until next field or end of string
    # Try with optional leading whitespace first
    pattern = rf"^\s*{field_name}:\s*(.+?)(?=\n\s*\w+:|$)"
    match = re.search(pattern, prompt_content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Try without ^ anchor (field anywhere in content)
    pattern = rf"\s*{field_name}:\s*(.+?)(?=\n\s*\w+:|$)"
    match = re.search(pattern, prompt_content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    
    return None

def make_code_preview_fn(*funcs: Callable):
    """Create a preview function with captured callable context."""
    def preview_fn() -> TextPreview:
        sources: list[str] = []

        for func in funcs:
            try:
                source = inspect.getsource(func)
                source = textwrap.dedent(source)
            except (OSError, TypeError):
                name = getattr(func, "__qualname__", repr(func))
                source = f"# Source unavailable for {name}"

            sources.append(source)

        return TextPreview(
            content="\n\n".join(sources),
            meta={"language": "python"},
        )

    return preview_fn