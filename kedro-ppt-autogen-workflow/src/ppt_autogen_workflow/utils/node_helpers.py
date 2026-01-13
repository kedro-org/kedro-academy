"""Shared helper functions for pipeline nodes."""
from __future__ import annotations

import json
import re
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

    # Handle structured dict with chart_path key
    if isinstance(content, dict):
        if 'chart_path' in content:
            return content.get('chart_path')
        # Extract from content_text if present (raw agent response)
        raw_text = content.get('content_text', '')
        if raw_text:
            return _extract_path_from_text(raw_text)

    if isinstance(content, str):
        if content.strip().startswith('{'):
            try:
                return json.loads(content).get('chart_path')
            except json.JSONDecodeError:
                pass
        # Try to extract path from raw text
        return _extract_path_from_text(content)

    return None


def _extract_path_from_text(text: str) -> str | None:
    """Extract file path from raw agent response text."""
    # Match patterns like "Chart Path: /path/to/file.png" or "chart_path: /path/to/file"
    patterns = [
        r'[Cc]hart[_ ][Pp]ath[:\s]+([/\w\-_.]+\.png)',
        r'[Cc]hart[_ ][Pp]ath[:\s]+[\'"]?([/\w\-_.]+\.png)[\'"]?',
        r'saved (?:to|at)[:\s]+[\'"]?([/\w\-_.]+\.png)[\'"]?',
        r'([/\w\-_.]+/chart[/\w\-_.]*\.png)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_summary_text(result: dict[str, Any]) -> str:
    """Extract summary text from agent result."""
    if not result.get('success'):
        return ""

    content = result.get('summary') or result.get('content', {})

    if isinstance(content, dict):
        # Check for summary_text key first (from summary tool)
        if 'summary_text' in content:
            return _clean_summary(content['summary_text'])
        # Check other common text keys
        text = content.get('text', '') or content.get('content', '')
        if text:
            return _clean_summary(text)
        # Extract from content_text if present (raw agent response)
        raw_text = content.get('content_text', '')
        if raw_text:
            return _extract_summary_from_text(raw_text)
        # Skip tool output dicts that don't contain summary (slide_path, chart_path, status, error)
        if any(k in content for k in ['slide_path', 'slidepath', 'chart_path', 'status', 'error']):
            return ""
        # Don't return stringified dicts as summary
        return ""

    if isinstance(content, str):
        if content.strip().startswith('{') or content.strip().startswith("{'"):
            try:
                parsed = json.loads(content.replace("'", '"'))
                if 'summary_text' in parsed:
                    return _clean_summary(parsed['summary_text'])
                # Skip tool output strings
                if any(k in parsed for k in ['slide_path', 'slidepath', 'chart_path', 'status', 'error']):
                    return ""
            except (json.JSONDecodeError, ValueError):
                pass
        return _extract_summary_from_text(content)

    # Don't return non-string content as summary
    return ""


def _extract_summary_from_text(text: str) -> str:
    """Extract summary bullets from raw agent response text."""
    # Try to parse as JSON first (tool output)
    clean_text = text.strip()
    if clean_text.startswith('{') or clean_text.startswith("{'"):
        try:
            # Handle both JSON and Python dict-like strings
            parsed = json.loads(clean_text.replace("'", '"'))
            # Check for summary_text key (from summary tool)
            if 'summary_text' in parsed:
                return _clean_summary(parsed['summary_text'])
            # Skip slide tool output (has slide_path or slidepath but no summary)
            if ('slide_path' in parsed or 'slidepath' in parsed) and 'summary_text' not in parsed:
                return ""
            # Check for error
            if 'error' in parsed:
                return ""
        except (json.JSONDecodeError, ValueError):
            pass

    # Find lines that start with bullet points or dashes
    lines = text.replace('\\n', '\n').split('\n')
    summary_lines = []
    in_summary_section = False

    # Metadata patterns to skip
    skip_patterns = [
        r'^[Cc]hart[_ ][Pp]ath[:\s]',
        r'^[Ss]ummary[_ ][Tt]ext[:\s]*$',
        r'^[Ss]lide[_ ][Pp]ath[:\s]',
        r'^[Ss]tatus[:\s]',
        r'^[Ii]nstruction[:\s]',
        r'^/var/folders/',
        r'^/tmp/',
    ]

    for line in lines:
        line = line.strip()
        # Skip JSON-like content
        if line.startswith('{') or line.startswith("{'"):
            continue
        # Skip metadata lines
        if any(re.match(pattern, line) for pattern in skip_patterns):
            continue
        # Check if we're entering a summary section
        if re.match(r'^[Ss]ummary[:\s]*$', line):
            in_summary_section = True
            continue
        # Check for bullet points (-, •, *, or numbered)
        if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+[\.\)]\s+', line):
            # Clean the line
            clean_line = re.sub(r'^[-•*\d\.\)]+\s*', '', line).strip()
            # Skip if it's a metadata line after removing bullet
            if any(re.match(pattern, clean_line) for pattern in skip_patterns):
                continue
            if clean_line and len(clean_line) > 10:
                summary_lines.append(clean_line)
        # Stop if we hit a section that's not summary
        elif in_summary_section and line and not line.startswith('-'):
            if re.match(r'^(Both|The chart|Chart|Note)', line):
                break

    if summary_lines:
        return _clean_summary('\n'.join(summary_lines))

    # Don't return raw JSON/dict as summary
    if clean_text.startswith('{') or clean_text.startswith("{'"):
        return ""
    return _clean_summary(text)


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
