"""Shared helper functions for pipeline nodes."""
from __future__ import annotations


def format_summary_text(summary_text: str) -> str:
    """Format and clean summary text for presentation.

    Cleans up the summary text by:
    - Removing empty/short lines
    - Filtering out slide title references
    - Removing placeholder text
    - Ensuring consistent bullet point formatting

    Args:
        summary_text: Raw summary text from agent

    Returns:
        Formatted summary text with bullet points
    """
    if not summary_text:
        return ""

    lines = summary_text.split('\n')
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if 'slide title' in line.lower() or 'slide_title' in line.lower():
            continue
        if any(p in line.lower() for p in ['$x', 'please fill', 'placeholder']):
            continue

        # Clean up markdown formatting
        line = line.replace('**', '').replace('*', '').replace('__', '')
        line = line.lstrip('•').lstrip('*').lstrip('-').strip()
        formatted_lines.append(f"• {line}" if not line.startswith('•') else line)

    return '\n'.join(formatted_lines) or f"• {summary_text.strip()}"
