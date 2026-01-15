"""Shared agent tools for MA and SA pipelines.

These tools give agents access to raw data and let them analyze on demand.
Agents receive data and instructions, then perform actual analysis.
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Callable

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def _render_chart(config: dict[str, Any], styling_params: dict[str, Any]) -> plt.Figure:
    """Render a chart based on configuration.
    
    This is a self-contained chart rendering function that creates matplotlib
    figures for different chart types. It should not depend on pipeline code.
    
    Args:
        config: Chart configuration dict with:
            - chart_type: "bar", "horizontal_bar", "pie", or "line"
            - x_column: Column name for x-axis/categories
            - y_column: Column name for y-axis/values
            - data_subset: List of dicts containing the data
            - primary_color: Primary color hex code
            - secondary_color: Secondary color hex code
            - title: Chart title
        styling_params: Styling parameters dict
    
    Returns:
        matplotlib Figure object
    """
    # Convert data_subset to DataFrame
    df = pd.DataFrame(config.get("data_subset", []))
    
    if df.empty:
        # Return empty figure if no data
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center")
        return fig
    
    chart_type = config.get("chart_type", "bar")
    x_column = config.get("x_column")
    y_column = config.get("y_column")
    primary_color = config.get("primary_color", "#1F4E79")
    secondary_color = config.get("secondary_color", "#DDDDDD")
    title = config.get("title", "")
    
    # Get color palette from styling params if available
    chart_colors = styling_params.get("chart_colors", [primary_color])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Prepare data
    if x_column and y_column and x_column in df.columns and y_column in df.columns:
        x_data = df[x_column].tolist()
        y_data = df[y_column].tolist()
    elif y_column and y_column in df.columns:
        # If only y_column, use index as x
        x_data = df.index.tolist()
        y_data = df[y_column].tolist()
    else:
        # Fallback: use first two columns
        x_data = df.iloc[:, 0].tolist()
        y_data = df.iloc[:, 1].tolist() if len(df.columns) > 1 else df.iloc[:, 0].tolist()
    
    # Render based on chart type
    if chart_type == "pie":
        # Pie chart
        ax.pie(
            y_data,
            labels=x_data,
            autopct='%1.1f%%',
            colors=chart_colors[:len(y_data)] if len(chart_colors) >= len(y_data) else [primary_color] * len(y_data),
            startangle=90,
        )
        ax.set_title(title, fontsize=14, fontweight='bold', color=primary_color)
        
    elif chart_type == "horizontal_bar":
        # Horizontal bar chart
        bars = ax.barh(
            range(len(x_data)),
            y_data,
            color=primary_color,
        )
        ax.set_yticks(range(len(x_data)))
        ax.set_yticklabels(x_data)
        ax.set_xlabel(y_column if y_column else "Value", fontsize=10)
        ax.set_title(title, fontsize=14, fontweight='bold', color=primary_color)
        ax.grid(axis='x', color=secondary_color, linestyle='--', alpha=0.5)
        ax.invert_yaxis()  # Top item first
        
    elif chart_type == "line":
        # Line chart
        ax.plot(
            x_data,
            y_data,
            color=primary_color,
            marker='o',
            linewidth=2,
            markersize=6,
        )
        ax.set_xlabel(x_column if x_column else "Category", fontsize=10)
        ax.set_ylabel(y_column if y_column else "Value", fontsize=10)
        ax.set_title(title, fontsize=14, fontweight='bold', color=primary_color)
        ax.grid(True, color=secondary_color, linestyle='--', alpha=0.5)
        plt.xticks(rotation=45, ha='right')
        
    else:
        # Default: vertical bar chart
        bars = ax.bar(
            x_data,
            y_data,
            color=primary_color,
        )
        ax.set_xlabel(x_column if x_column else "Category", fontsize=10)
        ax.set_ylabel(y_column if y_column else "Value", fontsize=10)
        ax.set_title(title, fontsize=14, fontweight='bold', color=primary_color)
        ax.grid(axis='y', color=secondary_color, linestyle='--', alpha=0.5)
        plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    return fig


def build_data_analysis_tools(sales_data: pd.DataFrame) -> list[Callable]:
    """Build data analysis tools that let agents query raw data.

    Agents can query data based on what they actually need from instructions.
    No pre-computation - agents analyze on demand.

    Args:
        sales_data: Raw sales DataFrame

    Returns:
        List of tool functions for data analysis
    """
    def analyze_data(query: str) -> str:
        """Analyze sales data based on a natural language query.

        Agent provides a query describing what analysis is needed.
        Tool performs the analysis and returns results.

        Args:
            query: Natural language query describing desired analysis

        Returns:
            JSON string with analysis results
        """
        try:
            df = sales_data.copy()
            query_lower = query.lower()
            result: dict[str, Any] = {
                "query": query,
                "source": "on-demand analysis",
            }

            # Analyze based on query - agent decides what's needed
            if "top" in query_lower and "product" in query_lower:
                # Extract top N from query
                top_n = 10  # default
                for n in (5, 10, 15, 20):
                    if f"top {n}" in query_lower:
                        top_n = n
                        break
                
                if "FY_Sales" in df.columns and "Product" in df.columns:
                    top_df = df.nlargest(top_n, "FY_Sales")
                    result["top_products"] = {
                        "count": top_n,
                        "products": top_df[["Product", "FY_Sales"]].to_dict("records"),
                        "total_sales": float(top_df["FY_Sales"].sum()),
                        "percentage_of_total": float((top_df["FY_Sales"].sum() / df["FY_Sales"].sum()) * 100) if df["FY_Sales"].sum() > 0 else 0,
                    }

            if "category" in query_lower and "Product_Category" in df.columns and "FY_Sales" in df.columns:
                category_stats = df.groupby("Product_Category")["FY_Sales"].agg(["sum", "count", "mean"]).round(0)
                category_stats["percentage"] = (category_stats["sum"] / df["FY_Sales"].sum() * 100).round(1)
                result["categories"] = category_stats.to_dict("index")

            if "region" in query_lower and "Region" in df.columns and "FY_Sales" in df.columns:
                regional_stats = df.groupby("Region")["FY_Sales"].agg(["sum", "count", "mean"]).round(0)
                regional_stats["percentage"] = (regional_stats["sum"] / df["FY_Sales"].sum() * 100).round(1)
                result["regions"] = regional_stats.to_dict("index")

            if any(term in query_lower for term in ("summary", "overall", "total", "global")):
                if "FY_Sales" in df.columns:
                    result["global"] = {
                        "total_sales": float(df["FY_Sales"].sum()),
                        "avg_sales": float(df["FY_Sales"].mean()),
                        "median_sales": float(df["FY_Sales"].median()),
                        "total_products": len(df),
                    }

            logger.info(f"Analyzed data for query: {query[:50]}...")
            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error analyzing data: {e}")
            return json.dumps({"error": f"Error analyzing data: {str(e)}"})

    return [analyze_data]


def build_chart_generator_tools(
    sales_data: pd.DataFrame,
    styling: dict[str, Any],
) -> list[Callable]:
    """Build chart generator tools that let agents generate charts from data.

    Agents provide chart instruction and data subset, tool generates chart.
    No pre-computed configs - agents decide what chart to create.

    Args:
        sales_data: Raw sales DataFrame
        styling: Styling parameters for charts

    Returns:
        List of tool functions for chart generator agent
    """
    def generate_chart(instruction: str, data_subset: list[dict[str, Any]] | None = None) -> str:
        """Generate a chart from instruction and data.

        Agent provides instruction and optionally a data subset.
        Tool parses instruction, filters data if needed, and generates chart.

        Args:
            instruction: Natural language chart instruction
            data_subset: Optional pre-filtered data (if agent already filtered)

        Returns:
            JSON string with chart_path and status
        """
        try:
            # Use provided data subset or full data
            if data_subset:
                df = pd.DataFrame(data_subset)
            else:
                df = sales_data.copy()

            # Parse instruction to determine chart type and columns
            instruction_lower = instruction.lower()
            
            # Detect chart type
            chart_type = "bar"
            if "horizontal bar" in instruction_lower:
                chart_type = "horizontal_bar"
            elif "pie" in instruction_lower:
                chart_type = "pie"
            elif "line" in instruction_lower:
                chart_type = "line"

            # Detect columns
            x_column = None
            y_column = None
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in instruction_lower:
                    if any(term in col_lower for term in ("sales", "revenue", "amount", "value")):
                        y_column = col
                    elif any(term in col_lower for term in ("product", "category", "region")):
                        x_column = col

            # Fallback column detection
            if not x_column:
                text_cols = df.select_dtypes(include=["object"]).columns
                x_column = text_cols[0] if len(text_cols) > 0 else df.columns[0]

            if not y_column:
                numeric_cols = df.select_dtypes(include=["number"]).columns
                y_column = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1] if len(df.columns) > 1 else df.columns[0]

            # Detect top N
            top_n = None
            for n in (5, 10, 15, 20):
                if f"top {n}" in instruction_lower:
                    top_n = n
                    break

            # Filter data if top_n specified
            if top_n and y_column:
                df = df.nlargest(top_n, y_column)

            # Create chart config
            config = {
                "chart_type": chart_type,
                "x_column": x_column,
                "y_column": y_column,
                "data_subset": df.to_dict("records"),
                "primary_color": styling.get("brand_color", "#1F4E79"),
                "secondary_color": styling.get("chart_secondary_color", "#DDDDDD"),
                "title": instruction[:100] if len(instruction) > 100 else instruction,
            }

            # Render chart
            fig = _render_chart(config, styling)

            # Save chart to temp file
            temp_dir = Path(tempfile.mkdtemp())
            chart_path = temp_dir / f"chart_{hash(instruction) % 10000}.png"
            fig.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"Generated {chart_type} chart from instruction")
            return json.dumps({
                "chart_path": str(chart_path),
                "chart_type": chart_type,
                "status": "success"
            }, indent=2)

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return json.dumps({"error": f"Error generating chart: {str(e)}"})

    return [generate_chart]


def build_summarizer_tools(
    sales_data: pd.DataFrame,
) -> list[Callable]:
    """Build summarizer tools that let agents analyze data and generate summaries.

    Agents provide instruction, tool analyzes data and generates insights.
    No pre-computed bullet points - agents generate insights from data.

    Args:
        sales_data: Raw sales DataFrame

    Returns:
        List of tool functions for summarizer agent
    """
    def generate_summary(instruction: str, data_subset: list[dict[str, Any]] | None = None) -> str:
        """Generate summary by analyzing data based on instruction.

        Agent provides instruction describing what summary is needed.
        Tool analyzes data and generates insights.

        Args:
            instruction: Natural language summary instruction
            data_subset: Optional pre-filtered data (if agent already filtered)

        Returns:
            JSON string with summary_text and status
        """
        try:
            # Use provided data subset or full data
            if data_subset:
                df = pd.DataFrame(data_subset)
            else:
                df = sales_data.copy()

            instruction_lower = instruction.lower()
            insights = []

            # Analyze based on instruction
            if "top" in instruction_lower and "product" in instruction_lower:
                if "FY_Sales" in df.columns and "Product" in df.columns:
                    top_n = 10
                    for n in (5, 10, 15, 20):
                        if f"top {n}" in instruction_lower:
                            top_n = n
                            break
                    
                    top_df = df.nlargest(top_n, "FY_Sales")
                    total_sales = df["FY_Sales"].sum()
                    top_sales = top_df["FY_Sales"].sum()
                    
                    insights.append(
                        f"• The top {top_n} products generated ${top_sales:,.0f} "
                        f"in total sales, representing {(top_sales / total_sales * 100):.1f}% of overall performance"
                    )
                    
                    if len(top_df) >= 2:
                        top_product = top_df.iloc[0]
                        second_product = top_df.iloc[1]
                        insights.append(
                            f"• {top_product['Product']} leads with ${top_product['FY_Sales']:,.0f}, "
                            f"followed by {second_product['Product']} at ${second_product['FY_Sales']:,.0f}"
                        )

            if "category" in instruction_lower and "Product_Category" in df.columns and "FY_Sales" in df.columns:
                category_stats = df.groupby("Product_Category")["FY_Sales"].sum().sort_values(ascending=False)
                if len(category_stats) > 0:
                    top_cat = category_stats.index[0]
                    top_cat_sales = category_stats.iloc[0]
                    total = category_stats.sum()
                    insights.append(
                        f"• {top_cat} dominates with ${top_cat_sales:,.0f} "
                        f"({(top_cat_sales / total * 100):.1f}% of total sales)"
                    )

            if "region" in instruction_lower and "Region" in df.columns and "FY_Sales" in df.columns:
                regional_stats = df.groupby("Region")["FY_Sales"].sum().sort_values(ascending=False)
                if len(regional_stats) > 0:
                    top_region = regional_stats.index[0]
                    top_region_sales = regional_stats.iloc[0]
                    total = regional_stats.sum()
                    insights.append(
                        f"• {top_region} leads regional performance with ${top_region_sales:,.0f} "
                        f"({(top_region_sales / total * 100):.1f}% of total)"
                    )

            if not insights:
                # Default insight if nothing matched
                if "FY_Sales" in df.columns:
                    total_sales = df["FY_Sales"].sum()
                    insights.append(f"• Total sales: ${total_sales:,.0f} across {len(df)} products")

            summary_text = "\n".join(insights)

            logger.info(f"Generated summary with {len(insights)} insights")
            return json.dumps({
                "summary_text": summary_text,
                "status": "success"
            }, indent=2)

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return json.dumps({"error": f"Error generating summary: {str(e)}"})

    return [generate_summary]


def build_critic_tools() -> list[Callable]:
    """Build critic tools (no data dependencies).

    Returns:
        List of tool functions for critic agent
    """
    # Critic tools don't need data - they review generated content
    return []


def build_sa_tools(
    sales_data: pd.DataFrame,
    styling: dict[str, Any],
) -> list[Callable]:
    """Build all tools for single-agent pipeline.

    The SA agent gets all tools in one bundle since it handles
    all tasks (analysis, charts, summaries) by itself.

    Args:
        sales_data: Raw sales DataFrame
        styling: Styling parameters for charts

    Returns:
        List of all tool functions for single agent
    """
    # Combine all tools into one bundle
    analysis_tools = build_data_analysis_tools(sales_data)
    chart_tools = build_chart_generator_tools(sales_data, styling)
    summary_tools = build_summarizer_tools(sales_data)

    # Return all tools for the single agent
    all_tools = analysis_tools + chart_tools + summary_tools

    logger.info(f"Built {len(all_tools)} tools for single agent")
    return all_tools
