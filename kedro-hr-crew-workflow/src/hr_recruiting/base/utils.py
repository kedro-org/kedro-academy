"""Shared utility functions used across pipelines."""

import time
from typing import Any

from crewai import Crew
from docx import Document


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
