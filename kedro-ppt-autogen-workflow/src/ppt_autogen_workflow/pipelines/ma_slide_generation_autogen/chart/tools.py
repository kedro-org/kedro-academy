"""Chart generation tools for the ChartGeneratorAgent.

This module provides tool builders that create FunctionTools
for chart generation, keeping all chart-related logic together.
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

from .generator import generate_chart_figure

logger = logging.getLogger(__name__)


def _create_chart_impl(instruction: str, sales_data: pd.DataFrame) -> str:
    """Generate chart from sales data.

    Args:
        instruction: Natural language chart specification
        sales_data: DataFrame with sales data

    Returns:
        JSON string with chart_path and status
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


def build_chart_generator_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the ChartGeneratorAgent.

    Chart generator needs chart creation capability.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for chart generator
    """
    def generate_sales_chart(instruction: str) -> str:
        """Generate a chart visualization from sales data.

        Args:
            instruction: Natural language description of the chart to create

        Returns:
            JSON with chart_path and status
        """
        return _create_chart_impl(instruction, sales_data)

    return [
        FunctionTool(
            generate_sales_chart,
            description="Generate chart visualization from sales data based on natural language instruction"
        )
    ]
