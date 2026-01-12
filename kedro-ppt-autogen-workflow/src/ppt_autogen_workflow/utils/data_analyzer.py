"""Data analysis utilities for sales data processing.

This module provides shared data analysis functions used by both
single-agent and multi-agent pipeline tools.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _convert_to_native_types(obj: Any) -> Any:
    """Convert numpy/pandas types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_to_native_types(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_to_native_types(item) for item in obj]
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return obj


def analyze_sales_data(
    query: str,
    df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Analyze sales data based on a natural language query.

    Extracts insights based on query keywords:
    - "top": Top products, regional performance, category performance
    - "summary" or "trend": Comprehensive business insights including
      totals, averages, top performer, category/regional breakdown

    Args:
        query: Natural language query describing desired analysis
        df: DataFrame containing sales data with expected columns:
            FY_Sales, Product, Product_Category, Region

    Returns:
        Dictionary containing analysis results with keys:
        - query: Original query string
        - data_shape: Dict with rows and columns counts
        - columns: List of column names
        - top_products: (if "top" in query) List of top 10 products
        - regional_performance: (if "top" in query) Dict of sales by region
        - category_performance: (if "top" in query) Dict of sales by category
        - total_sales, avg_sales, median_sales: (if "summary/trend") Aggregates
        - top_performer: (if "summary/trend") Dict with top product details
        - category_insights: (if "summary/trend") Category breakdown
        - regional_insights: (if "summary/trend") Regional breakdown
        - sample_data: First 3 rows of data
    """
    analysis: dict[str, Any] = {
        "query": query,
        "data_shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": list(df.columns),
    }

    query_lower = query.lower()

    # Top performers analysis
    if "top" in query_lower:
        analysis.update(_analyze_top_performers(df))

    # Comprehensive summary analysis
    if "summary" in query_lower or "trend" in query_lower:
        analysis.update(_analyze_summary(df))

    # Always include sample data
    if len(df) > 0:
        analysis["sample_data"] = df.head(3).to_dict("records")
    else:
        analysis["sample_data"] = []

    return analysis


def _analyze_top_performers(df: pd.DataFrame) -> dict[str, Any]:
    """Extract top performer metrics from sales data."""
    result: dict[str, Any] = {}

    if "FY_Sales" not in df.columns:
        return result

    if "Product" in df.columns:
        top_products = df.nlargest(10, "FY_Sales")[
            ["Product", "FY_Sales", "Product_Category"]
        ]
        result["top_products"] = top_products.to_dict("records")
        result["total_top_10_sales"] = top_products["FY_Sales"].sum()

    if "Region" in df.columns:
        regional_sales = (
            df.groupby("Region")["FY_Sales"].sum().sort_values(ascending=False)
        )
        result["regional_performance"] = regional_sales.to_dict()

    if "Product_Category" in df.columns:
        category_sales = (
            df.groupby("Product_Category")["FY_Sales"]
            .sum()
            .sort_values(ascending=False)
        )
        result["category_performance"] = category_sales.to_dict()

    return result


def _analyze_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Generate comprehensive business summary from sales data."""
    result: dict[str, Any] = {}

    if "FY_Sales" not in df.columns:
        return result

    # Basic aggregates
    result["total_sales"] = df["FY_Sales"].sum()
    result["avg_sales"] = df["FY_Sales"].mean()
    result["median_sales"] = df["FY_Sales"].median()
    result["total_products"] = len(df)

    # Top performer details
    top_idx = df["FY_Sales"].idxmax()
    top_product = df.loc[top_idx]
    result["top_performer"] = {
        "product": top_product["Product"],
        "sales": top_product["FY_Sales"],
        "category": top_product["Product_Category"],
        "region": top_product["Region"],
    }

    # Category breakdown
    if "Product_Category" in df.columns:
        category_stats = (
            df.groupby("Product_Category")["FY_Sales"]
            .agg(["sum", "count", "mean"])
            .round(0)
        )
        category_stats["percentage"] = (
            category_stats["sum"] / df["FY_Sales"].sum() * 100
        ).round(1)
        result["category_insights"] = category_stats.to_dict("index")

    # Regional breakdown
    if "Region" in df.columns:
        regional_stats = (
            df.groupby("Region")["FY_Sales"].agg(["sum", "count", "mean"]).round(0)
        )
        regional_stats["percentage"] = (
            regional_stats["sum"] / df["FY_Sales"].sum() * 100
        ).round(1)
        result["regional_insights"] = regional_stats.to_dict("index")

    return result


def analyze_sales_data_json(
    query: str,
    df: pd.DataFrame | None,
) -> str:
    """
    Analyze sales data and return JSON string result.

    Convenience wrapper around analyze_sales_data() that handles
    None DataFrames and JSON serialization.

    Args:
        query: Natural language query describing desired analysis
        df: DataFrame containing sales data, or None

    Returns:
        JSON string containing analysis results or error message
    """
    if df is None:
        return json.dumps({"error": "No sales data available"})

    try:
        analysis = analyze_sales_data(query, df.copy())
        analysis = _convert_to_native_types(analysis)
        return json.dumps(analysis, indent=2)
    except Exception as e:
        error_msg = f"Error analyzing sales data: {e}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})
