"""Prompt and skill diff utilities."""

from __future__ import annotations

import difflib
import html


def unified_diff_html(before: str, after: str, before_label: str = "Before", after_label: str = "After") -> str:
    """Render a unified diff as HTML with spec colour palette."""
    lines = list(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=before_label,
            tofile=after_label,
            lineterm="",
        )
    )
    if not lines:
        return "<pre>No changes detected.</pre>"

    body: list[str] = []
    for line in lines:
        css = ""
        if line.startswith("+") and not line.startswith("+++"):
            css = "background:#F0FFF4;"
        elif line.startswith("-") and not line.startswith("---"):
            css = "background:#FFF5F5;"
        escaped = html.escape(line.rstrip("\n"))
        body.append(f'<pre style="margin:0;padding:2px 8px;{css}">{escaped}</pre>')
    return (
        '<div style="font-family:monospace;font-size:13px;border:1px solid #E2E2E2;">'
        + "".join(body)
        + "</div>"
    )


def unified_diff_text(before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="before",
            tofile="after",
        )
    )
