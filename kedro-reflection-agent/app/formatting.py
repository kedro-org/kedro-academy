"""Shared display formatting helpers."""

from __future__ import annotations

# Keep in sync with conf/base/parameters.yml
DEFAULT_PASSING_THRESHOLD = 0.92

_AGENT_LABELS = {
    "b2b_sales": "B2B Sales",
    "consumer_mktg": "Consumer Marketing",
    "customer_care": "Customer Care",
}


def resolve_passing_threshold(stored_threshold: float | None = None) -> float:
    """Return the threshold used for a run, or the global default."""
    if stored_threshold is not None:
        return float(stored_threshold)
    return DEFAULT_PASSING_THRESHOLD


def pass_rate_explainer_html(
    agent_id: str,
    *,
    stored_threshold: float | None = None,
) -> str:
    """Short HTML explainer for pass rate vs avg score and the passing threshold."""
    threshold = resolve_passing_threshold(stored_threshold)
    label = _AGENT_LABELS.get(agent_id, agent_id.replace("_", " ").title())
    threshold_line = (
        f"Passing threshold for <strong>{label}</strong>: "
        f"<strong>{threshold:.0%}</strong> mean case score."
    )
    return f"""
    <div style="font-size:12px;color:#64748B;line-height:1.55;padding:10px 14px;
                background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;">
      <strong style="color:#475569;">Pass rate</strong> is the share of eval cases
      whose mean dimension score meets the passing bar
      (shown as <em>passing / total</em>).
      <span style="color:#94A3B8;">
        It differs from <strong style="color:#64748B;">Avg Score</strong>, which averages
        all case scores regardless of pass/fail.
      </span>
      <div style="margin-top:6px;color:#475569;">{threshold_line}</div>
    </div>
    """


def format_score_delta(delta: float, *, decimals: int = 2) -> str:
    """Format a numeric score delta, normalising -0.00 to +0.00."""
    rounded = round(float(delta), decimals)
    if rounded == 0:
        rounded = 0.0
    sign = "+" if rounded >= 0 else ""
    return f"{sign}{rounded:.{decimals}f}"


def score_delta_color(delta: float, *, decimals: int = 2) -> str:
    """Return green/red hex color for a score delta."""
    rounded = round(float(delta), decimals)
    if rounded == 0:
        rounded = 0.0
    return "#15803D" if rounded >= 0 else "#B91C1C"
