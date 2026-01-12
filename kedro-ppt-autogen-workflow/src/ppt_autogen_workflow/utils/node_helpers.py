"""Shared helper functions for pipeline nodes."""
from __future__ import annotations

import json
from typing import Any


def format_summary_text(summary_text: str) -> str:
    """Format and clean summary text for presentation."""
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

        line = line.lstrip('•').lstrip('*').lstrip('-').strip()
        formatted_lines.append(f"• {line}" if not line.startswith('•') else line)

    return '\n'.join(formatted_lines) or f"• {summary_text.strip()}"


def extract_chart_path(result: dict[str, Any]) -> str | None:
    """Extract chart path from agent result."""
    if not result.get('success'):
        return None

    content = result.get('chart_data') or result.get('content', {})

    if isinstance(content, dict):
        return content.get('chart_path')
    if isinstance(content, str) and content.strip().startswith('{'):
        try:
            return json.loads(content).get('chart_path')
        except json.JSONDecodeError:
            pass
    return None


def extract_summary_text(result: dict[str, Any]) -> str:
    """Extract summary text from agent result."""
    if not result.get('success'):
        return ""

    content = result.get('summary') or result.get('content', {})

    if isinstance(content, dict):
        text = content.get('summary_text', '') or content.get('text', '') or content.get('content', '')
        if not text:
            try:
                text = json.loads(str(content)).get('summary_text', '')
            except (json.JSONDecodeError, TypeError):
                text = str(content)
        return _clean_summary(text)

    if isinstance(content, str):
        if content.strip().startswith('{'):
            try:
                parsed = json.loads(content)
                text = parsed.get('summary_text', '') or parsed.get('text', '')
                if text:
                    return _clean_summary(text)
            except json.JSONDecodeError:
                pass
        return _clean_summary(content)

    return _clean_summary(str(content))


def _clean_summary(text: str) -> str:
    """Clean up markdown formatting from summary."""
    if not text:
        return ""
    text = text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
    return '\n'.join(line.strip() for line in text.split('\n') if line.strip())


def create_fallback_summary(slide_key: str, instruction: str = "") -> str:
    """Create fallback summary when agent fails."""
    if instruction:
        return f"• Analysis for {slide_key}\n• Data insights based on: {instruction[:100]}..."
    return f"• Analysis for {slide_key}\n• Data insights generated"
