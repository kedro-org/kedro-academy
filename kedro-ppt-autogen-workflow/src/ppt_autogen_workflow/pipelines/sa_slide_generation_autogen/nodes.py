"""Kedro nodes for single-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import logging
import tempfile
from typing import Any
from pathlib import Path

import pandas as pd

from autogen_ext.models.openai import OpenAIChatCompletionClient
from pptx import Presentation
from .agent import create_ppt_agent, PPTGenerationAgent

# Import utility functions
from ppt_autogen_workflow.utils.chart_generator import generate_chart
from ppt_autogen_workflow.utils.summary_generator import generate_summary
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def initialize_ppt_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame,
) -> PPTGenerationAgent:
    """Initialize and compile the PPT generation agent with sales data access.

    Args:
        model_client: Pre-configured OpenAIChatCompletionClient from dataset
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled PPTGenerationAgent ready for invocation
    """
    logger.info("Initializing PPT generation agent...")

    try:
        agent = create_ppt_agent(model_client, sales_data=sales_data)
        logger.info("✓ PPT agent initialized and compiled successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize PPT agent: {str(e)}")
        raise


def run_ppt_generation(
    agent: PPTGenerationAgent,
    instructions_yaml: dict[str, Any],
    sales_data: Any,
    user_query: str
) -> Any:
    """
    Generate PPT by parsing instructions_yaml and creating slides programmatically.
    
    Args:
        agent: Compiled agent (available for future use)
        instructions_yaml: Slide definitions with chart/summary instructions
        sales_data: Sales data DataFrame
        user_query: User request (for logging)
        
    Returns:
        Combined Presentation object
    """
    logger.info("=" * 80)
    logger.info("Starting single-agent PPT generation with instructions_yaml...")
    logger.info("=" * 80)
    
    try:
        # Parse instructions_yaml structure
        logger.info("Step 1: Parsing instructions_yaml structure...")
        slide_definitions = parse_instructions_yaml(instructions_yaml)
        logger.info(f"✓ Found {len(slide_definitions)} slide definitions in instructions_yaml")
        
        # Ensure sales_data is a DataFrame
        if not isinstance(sales_data, pd.DataFrame):
            if sales_data is not None:
                try:
                    sales_data = pd.DataFrame(sales_data)
                except Exception as e:
                    logger.warning(f"Could not convert sales_data to DataFrame: {e}, using empty DataFrame")
                    sales_data = pd.DataFrame()
            else:
                sales_data = pd.DataFrame()
        
        # Validate DataFrame is not empty
        if sales_data.empty:
            logger.warning("sales_data is empty - charts and summaries may not be generated correctly")
        
        slide_presentations = []
        
        # Process each slide definition
        for slide_key, slide_config in slide_definitions.items():
            logger.info("=" * 80)
            logger.info(f"Processing {slide_key}: {slide_config.get('objective', {}).get('slide_title', 'Untitled')}")
            logger.info("=" * 80)
            
            objective = slide_config.get('objective', {})
            chart_instruction = objective.get('chart_instruction', '')
            summary_instruction = objective.get('summary_instruction', '')
            slide_title = objective.get('slide_title', slide_key)
            
            # Generate chart for this slide
            logger.info(f"  Generating chart for {slide_key}...")
            chart_path, chart_fig = _generate_chart_for_slide(
                sales_data, chart_instruction, slide_key
            )
            if chart_fig:
                logger.info(f"  ✓ Chart generated: {chart_path}")
            else:
                logger.warning(f"  ⚠ Chart generation failed for {slide_key}")
            
            # Generate summary for this slide
            logger.info(f"  Generating summary for {slide_key}...")
            summary_text = _generate_summary_for_slide(
                sales_data, summary_instruction, slide_key
            )
            logger.info(f"  ✓ Summary generated ({len(summary_text)} chars)")
            
            # Create slide presentation
            logger.info(f"  Creating slide presentation for {slide_key}...")
            if chart_path and Path(chart_path).exists():
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path=chart_path,
                    summary_text=summary_text
                )
            else:
                # Create slide without chart if chart generation failed
                logger.warning(f"  Chart path not available for {slide_key}, creating slide without chart")
                slide_prs = Presentation()
                slide_layout = slide_prs.slide_layouts[1]  # Title and Content layout
                slide = slide_prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = slide_title
                slide.placeholders[1].text = summary_text if summary_text else f"Content for {slide_title}"
            
            slide_presentations.append(slide_prs)
            logger.info(f"✓ Slide {slide_key} created successfully\n")
        
        # Combine all slides into final presentation
        logger.info("=" * 80)
        logger.info("Step 2: Combining all slides into final presentation...")
        final_presentation = combine_presentations(slide_presentations)
        
        logger.info(f"✓ Single-agent PPT generation completed successfully - Created {len(slide_presentations)} slides")
        return final_presentation
        
    except Exception as e:
        logger.error(f"PPT generation failed: {str(e)}", exc_info=True)
        # Return a basic presentation with error information
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_placeholder = slide.shapes.title
        subtitle_placeholder = slide.placeholders[1]
        
        title_placeholder.text = "Error in Presentation Generation"
        subtitle_placeholder.text = f"Error: {str(e)}\nQuery: {user_query}"
        
        return prs


def _generate_chart_for_slide(
    sales_data: pd.DataFrame,
    chart_instruction: str,
    slide_key: str
) -> tuple[str, Any]:
    """Generate chart for a slide. Returns (chart_path, matplotlib.Figure)."""
    try:
        # Validate DataFrame
        if sales_data is None or (isinstance(sales_data, pd.DataFrame) and sales_data.empty):
            logger.warning(f"  ⚠ Empty or None sales_data for {slide_key}, cannot generate chart")
            return "", None
        
        # Use direct utility function for chart generation
        fig = generate_chart(sales_data, chart_instruction)
        
        # Save chart to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        # Don't close figure - we might need it later
        
        return str(chart_path), fig
        
    except Exception as e:
        logger.error(f"  ✗ Error generating chart for {slide_key}: {str(e)}")
        return "", None


def _generate_summary_for_slide(
    sales_data: pd.DataFrame,
    summary_instruction: str,
    slide_key: str
) -> str:
    """Generate summary text for a slide."""
    try:
        # Validate DataFrame
        if sales_data is None or (isinstance(sales_data, pd.DataFrame) and sales_data.empty):
            logger.warning(f"  ⚠ Empty or None sales_data for {slide_key}, using default summary")
            return f"• Analysis for {slide_key}\n• Data insights generated"
        
        # Use direct utility function for summary generation
        summary_text = generate_summary(sales_data, summary_instruction)
        return summary_text
        
    except Exception as e:
        logger.error(f"  ✗ Error generating summary for {slide_key}: {str(e)}")
        # Return default summary
        return f"• Analysis for {slide_key}\n• Data insights generated"

