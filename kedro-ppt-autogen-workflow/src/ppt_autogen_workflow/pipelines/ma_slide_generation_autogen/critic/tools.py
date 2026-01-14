"""QA tools for the CriticAgent.

This module provides tool builders that create FunctionTools
for the critic agent's quality assurance workflow.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from autogen_core.tools import FunctionTool

from ..presentation import create_slide

logger = logging.getLogger(__name__)


def _create_slide_impl(title: str, chart_path: str, summary: str) -> str:
    """Create PowerPoint slide.

    Args:
        title: Slide title
        chart_path: Path to chart image
        summary: Summary text

    Returns:
        JSON string with status and slide_path
    """
    try:
        import tempfile

        if not Path(chart_path).exists():
            return json.dumps({"error": f"Chart file not found: {chart_path}"})

        slide_summary = summary or f"Analysis of {title.lower()} showing key performance metrics."
        presentation = create_slide(slide_title=title, chart_path=chart_path, summary_text=slide_summary)

        temp_dir = Path(tempfile.mkdtemp())
        slide_path = temp_dir / f"slide_{title.replace(' ', '_')}.pptx"
        presentation.save(str(slide_path))

        return json.dumps({"status": "success", "slide_path": str(slide_path)}, indent=2)
    except Exception as e:
        logger.error(f"Error creating slide: {str(e)}")
        return json.dumps({"error": f"Error creating slide: {str(e)}"})


def build_critic_tools() -> list[FunctionTool]:
    """Build tools for the CriticAgent.

    Critic needs slide creation to validate final output.

    Returns:
        List of FunctionTools for critic
    """
    def create_slide_with_content(title: str, chart_path: str, summary: str) -> str:
        """Create a PowerPoint slide with chart and summary.

        Args:
            title: Slide title
            chart_path: Path to chart image file
            summary: Summary text content

        Returns:
            JSON with status and slide_path
        """
        return _create_slide_impl(title, chart_path, summary)

    return [
        FunctionTool(
            create_slide_with_content,
            description="Create PowerPoint slide with chart and summary content"
        )
    ]
