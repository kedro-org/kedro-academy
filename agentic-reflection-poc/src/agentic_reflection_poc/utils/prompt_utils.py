"""Helpers for prompt loading and text extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WEAK_PROMPT_MARKER = "write a short outreach email"

SEED_PROMPT: dict[str, str] = {
    "prompt": (
        "You are a B2B sales email assistant for a telecom company.\n"
        "Write a short outreach email promoting the given product to the given customer.\n"
        "Include a subject and body."
    )
}

SEED_SKILL = """# B2B Email Style Guide

- Be clear.
- Mention the product.
- Keep it concise.
"""


def prompt_text(campaign_prompt: Any) -> str:
    if isinstance(campaign_prompt, dict):
        return str(campaign_prompt.get("prompt", "")).strip()
    if hasattr(campaign_prompt, "prompt"):
        return str(getattr(campaign_prompt, "prompt", "")).strip()
    if hasattr(campaign_prompt, "compile"):
        try:
            return str(campaign_prompt.compile()).strip()
        except Exception:  # noqa: BLE001
            pass
    return str(campaign_prompt).strip()


def is_weak_prompt(text: str) -> bool:
    return WEAK_PROMPT_MARKER in text.lower()


def load_seed_prompt_yaml() -> dict[str, str]:
    return SEED_PROMPT


def load_seed_skill(project_root: Path | None = None) -> str:
    root = project_root or Path.cwd()
    path = root / "skills" / "b2b-email-style.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return SEED_SKILL
