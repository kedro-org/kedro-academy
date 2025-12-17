"""Font utilities for chart and presentation generation.

This module provides shared font detection and configuration utilities
used by both chart_generator and ppt_builder modules.
"""

from __future__ import annotations

import platform
from typing import Final


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
