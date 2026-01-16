"""Shared utility functions for agentic pipelines."""
from __future__ import annotations

import platform
from typing import Any, Final


def format_prompt(template: Any, **kwargs) -> str:
    """Format a prompt template with given kwargs."""
    if hasattr(template, 'format'):
        return template.format(**kwargs)
    return str(template)


def get_system_font() -> str:
    """Get the best available font for the current system."""
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    elif system == "Darwin":  # macOS
        return "Helvetica Neue"
    return "DejaVu Sans"


SYSTEM_FONT: Final[str] = get_system_font()
