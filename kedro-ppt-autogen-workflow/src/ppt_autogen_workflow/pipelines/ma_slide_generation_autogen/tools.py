"""Multi-agent PPT Generation Tools for AutoGen Pipeline.

This module provides tool builders for multi-agent pipeline agents.
Each agent type gets specific tools suited to its role.
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


def build_planner_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the PlannerAgent.

    Planner needs data lookup to analyze requirements and plan execution.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for planner
    """
    return [build_data_lookup_tool(sales_data)]


def build_chart_generator_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the ChartGeneratorAgent.

    Chart generator needs chart creation capability.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for chart generator
    """
    return [build_chart_tool(sales_data)]


def build_summarizer_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the SummarizerAgent.

    Summarizer needs summary generation capability.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for summarizer
    """
    return [build_summary_tool(sales_data)]


def build_critic_tools() -> list[FunctionTool]:
    """Build tools for the CriticAgent.

    Critic needs slide creation to validate final output.

    Returns:
        List of FunctionTools for critic
    """
    return [build_slide_tool()]
