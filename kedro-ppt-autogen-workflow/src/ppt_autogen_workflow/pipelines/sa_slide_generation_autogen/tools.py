"""Single-agent PPT Generation Tools for AutoGen Pipeline.

This module provides tool builders for single-agent pipeline.
The single agent gets all tools needed for complete PPT generation.
"""
from __future__ import annotations

import pandas as pd
from autogen_core.tools import FunctionTool

from ppt_autogen_workflow.utils.tools_common import (
    build_chart_tool,
    build_summary_tool,
    build_data_lookup_tool,
    build_slide_tool,
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
        build_data_lookup_tool(sales_data),
        build_chart_tool(sales_data),
        build_summary_tool(sales_data),
        build_slide_tool(),
    ]
