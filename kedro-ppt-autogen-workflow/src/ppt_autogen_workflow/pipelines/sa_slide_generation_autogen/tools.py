"""PPT Generation Tools for Single-Agent AutoGen Pipeline."""
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

try:
    from ppt_autogen_workflow.utils.chart_generator import generate_chart
    from ppt_autogen_workflow.utils.data_analyzer import analyze_sales_data_json
    from ppt_autogen_workflow.utils.ppt_builder import create_slide
    from ppt_autogen_workflow.utils.summary_generator import generate_summary
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False

logger = logging.getLogger(__name__)


def build_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build and return the list of tools for PPT generation."""
    return [
        build_data_lookup_tool(sales_data),
        build_chart_generation_tool(sales_data),
        build_summary_generation_tool(sales_data),
        build_slide_creation_tool(),
    ]


def build_data_lookup_tool(sales_data: pd.DataFrame = None) -> FunctionTool:
    """Build the data lookup tool."""
    def get_sales_data(query: str) -> str:
        """Look up sales data based on query to find insights and patterns."""
        return _get_sales_data_sync(query, sales_data)

    return FunctionTool(
        get_sales_data,
        description="Look up and analyze sales data based on query (e.g., 'top products', 'summary stats', 'regional performance')",
    )


def build_chart_generation_tool(sales_data: pd.DataFrame = None) -> FunctionTool:
    """Build the chart generation tool."""
    def generate_sales_chart(instruction: str) -> str:
        """Generate chart visualization from sales data based on instruction."""
        return _generate_sales_chart_sync(instruction, sales_data)

    return FunctionTool(
        generate_sales_chart,
        description="Generate chart visualization from sales data (e.g., 'bar chart of top 10 products by revenue', 'pie chart of category distribution')",
    )


def build_summary_generation_tool(sales_data: pd.DataFrame = None) -> FunctionTool:
    """Build the summary generation tool."""
    def generate_business_summary(instruction: str) -> str:
        """Generate business summary from sales data based on instruction."""
        return _generate_business_summary_sync(instruction, sales_data)
    
    return FunctionTool(
        generate_business_summary,
        description="Generate business summary with calculated values from sales data. Use this tool to get accurate summaries with actual numbers, not placeholders."
    )


def build_slide_creation_tool() -> FunctionTool:
    """Build the slide creation tool."""
    def create_slide_with_chart(title: str, chart_path: str, summary: str) -> str:
        """Create a PowerPoint slide with chart image and summary text."""
        return _create_slide_sync(title, chart_path, summary)

    return FunctionTool(
        create_slide_with_chart,
        description="Create a PowerPoint slide with title, chart image, and bullet-point summary",
    )


def _get_sales_data_sync(query: str, sales_data: pd.DataFrame = None) -> str:
    """Look up sales data based on query."""
    return analyze_sales_data_json(query, sales_data)


def _generate_sales_chart_sync(instruction: str, sales_data: pd.DataFrame = None) -> str:
    """Generate chart from sales data based on instruction."""
    try:
        if sales_data is None:
            return json.dumps({"error": "No sales data available"})
        
        if not TOOLS_AVAILABLE:
            return json.dumps({"error": "Chart generation tools not available"})
        
        df = sales_data.copy()
        fig = generate_chart(df, instruction)
        
        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{hash(instruction) % 10000}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        
        result_data = {
            "chart_path": str(chart_path),
            "instruction": instruction,
            "data_shape": {"rows": len(df), "columns": len(df.columns)},
            "status": "success"
        }
        
        return json.dumps(result_data, indent=2)
        
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return json.dumps({"error": f"Error generating chart: {str(e)}"})


def _generate_business_summary_sync(instruction: str, sales_data: pd.DataFrame = None) -> str:
    """Generate business summary from sales data based on instruction."""
    try:
        if sales_data is None:
            return json.dumps({"error": "No sales data available"})
        
        if not TOOLS_AVAILABLE:
            return json.dumps({"error": "Summary generation tools not available"})
        
        df = sales_data.copy()
        summary_text = generate_summary(df, instruction)
        
        result = {
            "summary_text": summary_text,
            "instruction": instruction,
            "data_shape": {"rows": len(df), "columns": len(df.columns)},
            "status": "success"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error generating business summary: {str(e)}")
        return json.dumps({"error": f"Error generating business summary: {str(e)}"})


def _create_slide_sync(title: str, chart_path: str, summary: str) -> str:
    """Create a PowerPoint slide with chart and summary."""
    try:
        if not TOOLS_AVAILABLE:
            return json.dumps({"error": "Slide creation tools not available"})
        
        chart_file = Path(chart_path)
        if not chart_file.exists():
            return json.dumps({"error": f"Chart file not found: {chart_path}"})
        
        slide_summary = summary
        if not summary or summary.strip() == "":
            slide_summary = f"Analysis of {title.lower()} showing key performance metrics and business insights."
        
        presentation = create_slide(
            slide_title=title,
            chart_path=chart_path,
            summary_text=slide_summary
        )
        
        temp_dir = Path(tempfile.mkdtemp())
        slide_path = temp_dir / f"slide_{title.replace(' ', '_')}.pptx"
        presentation.save(str(slide_path))
        
        result_data = {
            "status": "success",
            "slide_title": title,
            "slide_path": str(slide_path),
            "chart_path": chart_path
        }
        
        return json.dumps(result_data, indent=2)
        
    except Exception as e:
        logger.error(f"Error creating slide: {str(e)}")
        return json.dumps({"error": f"Error creating slide: {str(e)}"})
