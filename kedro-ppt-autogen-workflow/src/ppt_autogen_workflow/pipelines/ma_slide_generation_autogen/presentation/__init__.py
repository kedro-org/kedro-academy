"""Presentation module for PPT building utilities.

This module contains all PowerPoint presentation building logic
used by the assembly node and critic agent.
"""
from .builder import (
    create_slide,
    combine_presentations,
    format_summary_text,
)

__all__ = [
    "create_slide",
    "combine_presentations",
    "format_summary_text",
]
