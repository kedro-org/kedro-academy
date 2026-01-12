"""Shared tool implementations for AutoGen pipelines."""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt
from autogen_core.tools import FunctionTool

from ppt_autogen_workflow.utils.chart_generator import generate_chart
from ppt_autogen_workflow.utils.data_analyzer import analyze_sales_data_json
from ppt_autogen_workflow.utils.summary_generator import generate_summary
from ppt_autogen_workflow.utils.ppt_builder import create_slide

logger = logging.getLogger(__name__)


def create_chart_impl(instruction: str, sales_data: pd.DataFrame) -> str:
    """Generate chart from sales data."""
    try:
        if sales_data is None:
            return json.dumps({"error": "No sales data available"})

        fig = generate_chart(sales_data.copy(), instruction)
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


def create_summary_impl(instruction: str, sales_data: pd.DataFrame) -> str:
    """Generate summary from sales data."""
    try:
        if sales_data is None:
            return json.dumps({"error": "No sales data available"})

        summary_text = generate_summary(sales_data.copy(), instruction)
        return json.dumps({
            "summary_text": summary_text,
            "instruction": instruction,
            "status": "success"
        }, indent=2)
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return json.dumps({"error": f"Error generating summary: {str(e)}"})


def analyze_data_impl(query: str, sales_data: pd.DataFrame) -> str:
    """Analyze sales data based on query."""
    return analyze_sales_data_json(query, sales_data)


def create_slide_impl(title: str, chart_path: str, summary: str) -> str:
    """Create PowerPoint slide."""
    try:
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


def build_chart_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build chart generation tool."""
    def generate_sales_chart(instruction: str) -> str:
        return create_chart_impl(instruction, sales_data)
    return FunctionTool(generate_sales_chart, description="Generate chart from sales data")


def build_summary_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build summary generation tool."""
    def generate_business_summary(instruction: str) -> str:
        return create_summary_impl(instruction, sales_data)
    return FunctionTool(generate_business_summary, description="Generate business summary with actual values")


def build_data_lookup_tool(sales_data: pd.DataFrame) -> FunctionTool:
    """Build data lookup tool."""
    def analyze_sales_data(query: str) -> str:
        return analyze_data_impl(query, sales_data)
    return FunctionTool(analyze_sales_data, description="Analyze sales data for insights")


def build_slide_tool() -> FunctionTool:
    """Build slide creation tool."""
    def create_slide_with_content(title: str, chart_path: str, summary: str) -> str:
        return create_slide_impl(title, chart_path, summary)
    return FunctionTool(create_slide_with_content, description="Create PowerPoint slide")
