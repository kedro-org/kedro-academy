"""Shared utility functions for agentic pipelines.

This module contains utility functions that are reused across
both multi-agent and single-agent pipelines.
"""
from __future__ import annotations

import platform
from typing import Any, Final


def format_prompt(template: Any, **kwargs) -> str:
    """Format a prompt template with given kwargs.
    
    This is a generic prompt formatting function that handles both
    objects with a .format() method and plain strings.
    
    Args:
        template: Prompt template (can be a string or object with format method)
        **kwargs: Keyword arguments to format into the template
        
    Returns:
        Formatted prompt string
    """
    if hasattr(template, 'format'):
        return template.format(**kwargs)
    return str(template)


def get_system_font() -> str:
    """Get the best available font for the current system.

    Returns:
        Font name appropriate for the current operating system:
        - Windows: "Segoe UI"
        - macOS: "Helvetica Neue"
        - Linux/other: "DejaVu Sans"
    """
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    elif system == "Darwin":  # macOS
        return "Helvetica Neue"
    return "DejaVu Sans"  # Linux and others


# Pre-computed system font for performance
SYSTEM_FONT: Final[str] = get_system_font()
