"""Chart generation tool - Pure functions for creating charts from data."""
from __future__ import annotations

import logging
import re
import warnings
from dataclasses import dataclass
from typing import Any, Final

import matplotlib.pyplot as plt
import pandas as pd

from ppt_autogen_workflow.utils.fonts import SYSTEM_FONT

# Suppress font warnings
warnings.filterwarnings("ignore", message="findfont")
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

logger = logging.getLogger(__name__)

# Chart color palette
CHART_COLORS: Final[tuple[str, ...]] = (
    "#1F4E79", "#D0582A", "#70AD47", "#FFC000", "#5B9BD5", "#A5A5A5"
)


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    chart_type: str = "bar"
    x_column: str | None = None
    y_column: str | None = None
    primary_color: str = "#1F4E79"
    secondary_color: str = "#DDDDDD"
    top_n: int | None = None
    sort_order: str = "desc"
    title: str = ""
    show_labels: bool = True


def parse_chart_instruction(
    instruction: str,
    df: pd.DataFrame,
    styling_params: dict[str, Any] | None = None,
) -> ChartConfig:
    """
    Parse natural language chart instructions into configuration.

    Args:
        instruction: Natural language chart specification
        df: DataFrame with data
        styling_params: Optional styling parameters

    Returns:
        ChartConfig with parsed settings
    """
    params = styling_params or {}
    config = ChartConfig(
        primary_color=params.get("brand_color", "#1F4E79"),
        secondary_color=params.get("chart_secondary_color", "#DDDDDD"),
    )

    instruction_lower = instruction.lower()

    # Detect chart type
    if "horizontal bar" in instruction_lower:
        config.chart_type = "horizontal_bar"
    elif "pie chart" in instruction_lower:
        config.chart_type = "pie"
    elif "line chart" in instruction_lower:
        config.chart_type = "line"

    # Detect columns from instruction
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in instruction_lower:
            if any(term in col_lower for term in ("sales", "revenue", "amount", "value")):
                config.y_column = col
            elif any(term in col_lower for term in ("product", "category", "region")):
                config.x_column = col

    # Fallback column detection
    if not config.x_column:
        text_cols = df.select_dtypes(include=["object"]).columns
        config.x_column = text_cols[0] if len(text_cols) > 0 else df.columns[0]

    if not config.y_column:
        numeric_cols = df.select_dtypes(include=["number"]).columns
        config.y_column = numeric_cols[0] if len(numeric_cols) > 0 else df.columns[1]

    # Detect top N
    for n in (5, 10, 15, 20):
        if f"top {n}" in instruction_lower:
            config.top_n = n
            break

    # Extract colors from instruction
    hex_colors = re.findall(r"#[0-9A-Fa-f]{6}", instruction)
    if hex_colors:
        config.primary_color = hex_colors[0]
        if len(hex_colors) > 1:
            config.secondary_color = hex_colors[1]

    return config


def generate_chart(
    df: pd.DataFrame,
    chart_instruction: str,
    styling_params: dict[str, Any] | None = None,
) -> plt.Figure:
    """
    Generate chart visualization from DataFrame.

    This is a pure function that returns a matplotlib Figure object.
    The figure can be saved to disk via Kedro's MatplotlibWriter dataset.

    Args:
        df: Input DataFrame with data to visualize
        chart_instruction: Natural language chart specification
        styling_params: Optional styling parameters

    Returns:
        matplotlib Figure object
    """
    params = styling_params or {}
    config = parse_chart_instruction(chart_instruction, df, params)
    
    df_chart = df.copy()

    # Apply filters
    if config.top_n and config.y_column:
        df_chart = df_chart.nlargest(config.top_n, config.y_column)

    if config.sort_order == "desc" and config.y_column:
        df_chart = df_chart.sort_values(config.y_column, ascending=False)

    # Create figure
    plt.style.use("default")
    fig, ax = plt.subplots(figsize=(12, 8))

    text_font = params.get("text_font", SYSTEM_FONT)

    if config.chart_type == "horizontal_bar":
        _draw_horizontal_bar(ax, df_chart, config, text_font)
    elif config.chart_type == "bar":
        _draw_vertical_bar(ax, df_chart, config, text_font)
    elif config.chart_type == "line":
        _draw_line_chart(ax, df_chart, config, text_font)
    elif config.chart_type == "pie":
        _draw_pie_chart(ax, df_chart, config)

    if config.title:
        ax.set_title(
            config.title,
            fontsize=16,
            fontweight="bold",
            fontname=text_font,
        )

    # Apply common styling for non-pie charts
    if config.chart_type != "pie":
        axis = "x" if config.chart_type == "horizontal_bar" else "y"
        ax.grid(True, alpha=0.3, color=config.secondary_color, axis=axis)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    plt.tight_layout()
    
    logger.info(f"Generated {config.chart_type} chart")
    return fig


def _draw_horizontal_bar(ax, df: pd.DataFrame, config: ChartConfig, font: str) -> None:
    """Draw horizontal bar chart."""
    bars = ax.barh(
        df[config.x_column],
        df[config.y_column],
        color=config.primary_color,
    )
    ax.set_xlabel(config.y_column, fontsize=12, fontname=font)
    ax.set_ylabel(config.x_column, fontsize=12, fontname=font)

    if config.show_labels:
        for bar in bars:
            width = bar.get_width()
            ax.text(
                width + width * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=10,
                fontname=font,
            )


def _draw_vertical_bar(ax, df: pd.DataFrame, config: ChartConfig, font: str) -> None:
    """Draw vertical bar chart."""
    bars = ax.bar(
        df[config.x_column],
        df[config.y_column],
        color=config.primary_color,
    )
    ax.set_xlabel(config.x_column, fontsize=12, fontname=font)
    ax.set_ylabel(config.y_column, fontsize=12, fontname=font)

    if config.show_labels:
        for bar in bars:
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{int(height):,}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontname=font,
            )

    # Rotate labels if needed
    if len(str(df[config.x_column].iloc[0])) > 10:
        plt.xticks(rotation=45, ha="right")


def _draw_line_chart(ax, df: pd.DataFrame, config: ChartConfig, font: str) -> None:
    """Draw line chart."""
    ax.plot(
        df[config.x_column],
        df[config.y_column],
        color=config.primary_color,
        marker="o",
        linewidth=2,
        markersize=6,
    )
    ax.set_xlabel(config.x_column, fontsize=12, fontname=font)
    ax.set_ylabel(config.y_column, fontsize=12, fontname=font)

    if config.show_labels:
        for x, y in zip(df[config.x_column], df[config.y_column]):
            ax.annotate(
                f"{int(y):,}",
                (x, y),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=9,
                fontname=font,
            )

    if len(str(df[config.x_column].iloc[0])) > 10:
        plt.xticks(rotation=45, ha="right")


def _draw_pie_chart(ax, df: pd.DataFrame, config: ChartConfig) -> None:
    """Draw pie chart."""
    if any(term in config.x_column.lower() for term in ("category", "region")):
        pie_data = df.groupby(config.x_column)[config.y_column].sum()
    else:
        pie_data = df.set_index(config.x_column)[config.y_column]

    ax.pie(
        pie_data.values,
        labels=pie_data.index,
        autopct="%1.1f%%",
        colors=CHART_COLORS[: len(pie_data)],
    )
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))