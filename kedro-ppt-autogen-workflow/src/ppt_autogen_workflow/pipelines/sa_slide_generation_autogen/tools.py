"""Single-agent PPT Generation Tools for AutoGen Pipeline.

This module provides tool builders for single-agent pipeline.
The single agent gets all tools needed for complete PPT generation.

Tools are built by importing logic from MA pipeline's domain modules,
demonstrating code reuse across pipelines.
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import pandas as pd
from autogen_core.tools import FunctionTool

# Import business logic from MA pipeline's domain modules
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.planner.analyzer import (
    analyze_sales_data_json,
)
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.chart.generator import (
    generate_chart_figure,
)
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.summary.generator import (
    generate_summary_text,
)

logger = logging.getLogger(__name__)


def _build_data_lookup_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build data lookup tool for analyzing sales data.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        FunctionTool for data lookup
    """
    def analyze_sales_data(query: str) -> str:
        """Analyze sales data based on a natural language query.

        Args:
            query: Natural language query describing desired analysis

        Returns:
            JSON with analysis results
        """
        return analyze_sales_data_json(query, sales_data)

    return FunctionTool(
        analyze_sales_data,
        description="Analyze sales data for insights based on natural language query"
    )


def _build_chart_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build chart generation tool.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        FunctionTool for chart generation
    """
    def generate_sales_chart(instruction: str) -> str:
        """Generate a chart visualization from sales data.

        Args:
            instruction: Natural language description of the chart to create

        Returns:
            JSON with chart_path and status
        """
        try:
            if sales_data is None:
                return json.dumps({"error": "No sales data available"})

            fig = generate_chart_figure(sales_data.copy(), instruction)
            temp_dir = Path(tempfile.mkdtemp())
            chart_path = temp_dir / f"chart_{hash(instruction) % 10000}.png"
            fig.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close(fig)

            return json.dumps({
                "chart_path": str(chart_path),
                "instruction": instruction,
                "status": "success"
            }, indent=2)
        except Exception as e:
            logger.error(f"Error creating chart: {str(e)}")
            return json.dumps({"error": f"Error creating chart: {str(e)}"})

    return FunctionTool(
        generate_sales_chart,
        description="Generate chart visualization from sales data based on natural language instruction"
    )


def _build_summary_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build summary generation tool.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        FunctionTool for summary generation
    """
    def generate_business_summary(instruction: str) -> str:
        """Generate a business summary with bullet points from sales data.

        Args:
            instruction: Natural language description of the summary to create

        Returns:
            JSON with summary_text and status
        """
        try:
            if sales_data is None:
                return json.dumps({"error": "No sales data available"})

            summary_text = generate_summary_text(sales_data.copy(), instruction)
            return json.dumps({
                "summary_text": summary_text,
                "instruction": instruction,
                "status": "success"
            }, indent=2)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return json.dumps({"error": f"Error generating summary: {str(e)}"})

    return FunctionTool(
        generate_business_summary,
        description="Generate business summary with actual values from sales data"
    )


def _build_slide_tool() -> FunctionTool:
    """Build slide validation tool.

    Note: This tool validates slide creation capability. Actual slide creation
    happens in agent_helpers.py via create_slide_presentation(). This tool
    exists for agent reasoning about slide structure.

    Returns:
        FunctionTool for slide validation
    """
    def validate_slide_parameters(
        title: str,
        chart_path: str = "",
        summary_text: str = "",
    ) -> str:
        """Validate parameters for PowerPoint slide creation.

        This tool validates that slide parameters are correctly structured.
        Actual slide creation is handled by the pipeline's assembly step.

        Args:
            title: Slide title (required)
            chart_path: Path to chart image (optional)
            summary_text: Summary text for slide (optional)

        Returns:
            JSON with validation status
        """
        try:
            if not title or not title.strip():
                return json.dumps({"error": "Title is required and cannot be empty"})

            return json.dumps({
                "status": "valid",
                "title": title,
                "has_chart": bool(chart_path),
                "has_summary": bool(summary_text),
                "message": "Slide parameters validated successfully"
            }, indent=2)
        except Exception as e:
            logger.error(f"Error validating slide parameters: {str(e)}")
            return json.dumps({"error": f"Error validating slide: {str(e)}"})

    return FunctionTool(
        validate_slide_parameters,
        description="Validate slide parameters before creation"
    )


def build_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build all tools for PPTGenerationAgent.

    Single agent needs all tools for complete presentation generation:
    - Data lookup for analysis
    - Chart generation for visualizations
    - Summary generation for insights
    - Slide creation for final output

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of all FunctionTools needed for PPT generation
    """
    return [
        _build_data_lookup_tool(sales_data),
        _build_chart_tool(sales_data),
        _build_summary_tool(sales_data),
        _build_slide_tool(),
    ]
