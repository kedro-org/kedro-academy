"""Summary generation logic for creating business summaries.

This module contains all summary generation functionality used by the
SummarizerAgent, including data analysis and bullet point generation.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def analyze_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Analyze dataframe and extract insights.

    Args:
        df: Input DataFrame

    Returns:
        Dictionary of insights including sales, category, and regional analysis
    """
    insights: dict[str, Any] = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "numeric_columns": df.select_dtypes(include=["number"]).columns.tolist(),
        "categorical_columns": df.select_dtypes(include=["object"]).columns.tolist(),
    }

    # Find relevant columns
    sales_cols = [
        col for col in df.columns
        if any(term in col.lower() for term in ("sales", "revenue", "amount", "value"))
    ]
    category_cols = [
        col for col in df.columns
        if any(term in col.lower() for term in ("category", "type", "group"))
    ]
    region_cols = [
        col for col in df.columns
        if any(term in col.lower() for term in ("region", "location", "area"))
    ]

    # Sales analysis
    if sales_cols:
        sales_col = sales_cols[0]
        insights["sales_analysis"] = {
            "column": sales_col,
            "total_sales": float(df[sales_col].sum()),
            "avg_sales": float(df[sales_col].mean()),
            "max_sales": float(df[sales_col].max()),
            "min_sales": float(df[sales_col].min()),
            "top_performers": df.nlargest(10, sales_col).to_dict("records"),
        }

    # Category analysis
    if category_cols and sales_cols:
        category_col = category_cols[0]
        sales_col = sales_cols[0]
        category_sales = df.groupby(category_col)[sales_col].sum().to_dict()
        insights["category_analysis"] = {
            "column": category_col,
            "category_sales": {k: float(v) for k, v in category_sales.items()},
            "total_categories": len(category_sales),
        }

    # Regional analysis
    if region_cols and sales_cols:
        region_col = region_cols[0]
        sales_col = sales_cols[0]
        regional_sales = df.groupby(region_col)[sales_col].sum().to_dict()
        insights["regional_analysis"] = {
            "column": region_col,
            "regional_sales": {k: float(v) for k, v in regional_sales.items()},
            "total_regions": len(regional_sales),
        }

    return insights


def generate_summary_text(
    df: pd.DataFrame,
    summary_instruction: str,
) -> str:
    """Generate business summary from DataFrame.

    This is a pure function that returns formatted summary text.

    Args:
        df: Input DataFrame
        summary_instruction: Summary generation instructions

    Returns:
        Formatted bullet point summary text
    """
    insights = analyze_dataframe(df)
    instruction_lower = summary_instruction.lower()

    bullet_points: list[str] = []

    # Sales-based content
    if "sales_analysis" in insights and any(
        term in instruction_lower for term in ("sales", "top", "product")
    ):
        bullet_points.extend(_generate_sales_bullets(df, insights, instruction_lower))

    # Category-based content
    if "category_analysis" in insights and "category" in instruction_lower:
        bullet_points.extend(_generate_category_bullets(insights))

    # Regional content
    if "regional_analysis" in insights and "region" in instruction_lower:
        bullet_points.extend(_generate_regional_bullets(insights))

    # Default content if no bullets generated
    if not bullet_points:
        bullet_points = [
            f"• Dataset contains {insights['total_rows']} records providing comprehensive business insights",
            "• Analysis reveals key performance indicators for strategic decision-making",
        ]

    logger.info(f"Generated summary with {len(bullet_points)} bullet points")
    return "\n".join(bullet_points)


def _generate_sales_bullets(
    df: pd.DataFrame,
    insights: dict[str, Any],
    instruction_lower: str,
) -> list[str]:
    """Generate sales-related bullet points."""
    bullets: list[str] = []
    sales_data = insights["sales_analysis"]
    total_sales = sales_data["total_sales"]
    top_performers = sales_data.get("top_performers", [])

    top_n = next(
        (n for n in (5, 10, 15, 20) if f"top {n}" in instruction_lower),
        10,
    )

    if not top_performers:
        return bullets

    top_subset = top_performers[:top_n]
    top_sales = sum(item[sales_data["column"]] for item in top_subset)

    bullets.append(
        f"• The top {len(top_subset)} products generated ${top_sales:,.0f} in total sales, "
        f"representing {(top_sales / total_sales) * 100:.1f}% of overall performance"
    )

    if len(top_performers) >= 2:
        top_product = top_performers[0]
        second_product = top_performers[1]
        product_col = next(
            (col for col in df.columns if "product" in col.lower()),
            df.select_dtypes(include=["object"]).columns[0],
        )

        if product_col in top_product:
            bullets.append(
                f"• {top_product[product_col]} leads with ${top_product[sales_data['column']]:,.0f}, "
                f"followed by {second_product[product_col]} at ${second_product[sales_data['column']]:,.0f}"
            )

    remaining = len(df) - top_n
    if remaining > 0:
        remaining_sales = total_sales - top_sales
        concentration = (
            "strong concentration" if (top_sales / total_sales) > 0.7
            else "balanced distribution"
        )
        bullets.append(
            f"• The remaining {remaining} products contribute ${remaining_sales:,.0f}, "
            f"indicating {concentration} among performers"
        )

    return bullets


def _generate_category_bullets(insights: dict[str, Any]) -> list[str]:
    """Generate category-related bullet points."""
    bullets: list[str] = []
    cat_data = insights["category_analysis"]

    if not cat_data.get("category_sales"):
        return bullets

    sorted_cats = sorted(
        cat_data["category_sales"].items(),
        key=lambda x: x[1],
        reverse=True,
    )
    total_cat_sales = sum(cat_data["category_sales"].values())

    top_cat = sorted_cats[0]
    bullets.append(
        f"• {top_cat[0]} dominates with ${top_cat[1]:,.0f} "
        f"({(top_cat[1] / total_cat_sales) * 100:.1f}% of total sales)"
    )

    if len(sorted_cats) >= 2:
        second_cat = sorted_cats[1]
        bullets.append(
            f"• {second_cat[0]} follows with ${second_cat[1]:,.0f} "
            f"({(second_cat[1] / total_cat_sales) * 100:.1f}%)"
        )

    bullets.append(
        f"• Total of {len(sorted_cats)} categories analyzed with "
        f"combined sales of ${total_cat_sales:,.0f}"
    )

    return bullets


def _generate_regional_bullets(insights: dict[str, Any]) -> list[str]:
    """Generate regional-related bullet points."""
    bullets: list[str] = []
    regional_data = insights["regional_analysis"]

    if not regional_data.get("regional_sales"):
        return bullets

    sorted_regions = sorted(
        regional_data["regional_sales"].items(),
        key=lambda x: x[1],
        reverse=True,
    )
    total_regional_sales = sum(regional_data["regional_sales"].values())

    top_region = sorted_regions[0]
    bottom_region = sorted_regions[-1]

    bullets.append(
        f"• {top_region[0]} leads regional performance with ${top_region[1]:,.0f} "
        f"({(top_region[1] / total_regional_sales) * 100:.1f}% of total)"
    )

    if len(sorted_regions) >= 2:
        bullets.append(
            f"• {bottom_region[0]} presents growth opportunities at ${bottom_region[1]:,.0f} "
            f"({(bottom_region[1] / total_regional_sales) * 100:.1f}%)"
        )

    bullets.append(
        f"• Geographic distribution spans {len(sorted_regions)} regions with "
        f"total sales of ${total_regional_sales:,.0f}"
    )

    return bullets
