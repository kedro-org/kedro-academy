"""Summary generation tools for the SummarizerAgent.

This module provides tool builders that create FunctionTools
for summary generation, keeping all summary-related logic together.
"""
from __future__ import annotations

import json
import logging

import pandas as pd
from autogen_core.tools import FunctionTool

from .generator import generate_summary_text

logger = logging.getLogger(__name__)


def _create_summary_impl(instruction: str, sales_data: pd.DataFrame) -> str:
    """Generate summary from sales data.

    Args:
        instruction: Natural language summary specification
        sales_data: DataFrame with sales data

    Returns:
        JSON string with summary_text and status
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


def build_summarizer_tools(sales_data: pd.DataFrame = None) -> list[FunctionTool]:
    """Build tools for the SummarizerAgent.

    Summarizer needs summary generation capability.

    Args:
        sales_data: DataFrame with sales data

    Returns:
        List of FunctionTools for summarizer
    """
    def generate_business_summary(instruction: str) -> str:
        """Generate a business summary with bullet points from sales data.

        Args:
            instruction: Natural language description of the summary to create

        Returns:
            JSON with summary_text and status
        """
        return _create_summary_impl(instruction, sales_data)

    return [
        FunctionTool(
            generate_business_summary,
            description="Generate business summary with actual values from sales data"
        )
    ]
