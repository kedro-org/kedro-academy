"""Data analysis tools for the PlannerAgent.

This module provides tool builders that create FunctionTools
for data analysis, keeping all planner-related logic together.
"""
from __future__ import annotations

import pandas as pd
from autogen_core.tools import FunctionTool

from .analyzer import analyze_sales_data_json


def build_planner_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the PlannerAgent.

    Planner needs data lookup to analyze requirements and plan execution.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for planner
    """
    def analyze_sales_data(query: str) -> str:
        """Analyze sales data based on a natural language query.

        Args:
            query: Natural language query describing desired analysis

        Returns:
            JSON with analysis results
        """
        return analyze_sales_data_json(query, sales_data)

    return [
        FunctionTool(
            analyze_sales_data,
            description="Analyze sales data for insights based on natural language query"
        )
    ]
