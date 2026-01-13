"""Agent helper functions for single-agent PPT generation pipeline.

This module contains helper functions that work with the PPT generation agent
to generate charts and summaries. These are separated from nodes.py to keep
node functions focused on Kedro pipeline logic while agent-specific operations
are encapsulated here.
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from pptx import Presentation

from .agent import PPTGenerationAgent
from ppt_autogen_workflow.utils.ppt_builder import create_slide
from ppt_autogen_workflow.utils.node_helpers import (
    extract_chart_path,
    extract_summary_text,
    create_fallback_summary,
)

logger = logging.getLogger(__name__)


def generate_chart(
    agent: PPTGenerationAgent, user_prompt: str, slide_key: str, chart_instruction: str = ""
) -> tuple[str, plt.Figure | None]:
    """Generate chart for a slide using agent with formatted prompt.

    Args:
        agent: Compiled PPT generation agent
        user_prompt: Formatted user prompt for the slide
        slide_key: Unique identifier for the slide
        chart_instruction: Chart instruction for fallback

    Returns:
        Tuple of (chart_path, matplotlib_figure)
    """
    try:
        query = f"{user_prompt}\n\nTask: Generate a chart using the generate_sales_chart tool."
        chart_result = asyncio.run(agent.invoke(query))
        chart_path = extract_chart_path(chart_result)

        if chart_path and Path(chart_path).exists():
            try:
                from matplotlib.image import imread
                img = imread(chart_path)
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(img)
                ax.axis('off')
                return str(chart_path), fig
            except Exception as e:
                logger.warning(f"Could not load chart image: {e}")

        # Fallback: create placeholder chart
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{chart_instruction[:50]}...",
                ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")

        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        return str(chart_path), fig

    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        return "", None


def generate_summary(
    agent: PPTGenerationAgent, user_prompt: str, slide_key: str, chart_path: str = None
) -> str:
    """Generate summary text for a slide using agent with formatted prompt.

    Args:
        agent: Compiled PPT generation agent
        user_prompt: Formatted user prompt for the slide
        slide_key: Unique identifier for the slide
        chart_path: Path to generated chart for status

    Returns:
        Generated summary text
    """
    try:
        chart_status = f"Chart generated: {chart_path}" if chart_path and Path(chart_path).exists() else "Chart generation in progress"
        query = f"""{user_prompt}

Task: Generate a summary using the generate_business_summary tool.
Chart Status: {chart_status}

Use actual calculated values, not placeholders."""

        summary_result = asyncio.run(agent.invoke(query))
        summary_text = extract_summary_text(summary_result)
        return summary_text if summary_text else create_fallback_summary(slide_key, user_prompt)

    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return create_fallback_summary(slide_key, user_prompt)


def create_slide_presentation(title: str, chart_path: str | None, summary: str) -> Presentation:
    """Create a single slide presentation.

    Args:
        title: Slide title
        chart_path: Path to chart image
        summary: Summary text

    Returns:
        Presentation object with single slide
    """
    chart = chart_path if chart_path and Path(chart_path).exists() else ""
    return create_slide(slide_title=title, chart_path=chart, summary_text=summary)


def create_error_presentation(error_message: str) -> Presentation:
    """Create error presentation when generation fails.

    Args:
        error_message: Error message to display

    Returns:
        Presentation object with error slide
    """
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Error in Presentation Generation"
    slide.placeholders[1].text = f"Error: {error_message}"
    return prs
