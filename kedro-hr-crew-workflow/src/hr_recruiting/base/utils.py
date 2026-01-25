"""Shared utility functions used across pipelines."""

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
