"""Nodes for the ``apply`` pipeline.

Applies an approved reflection proposal:
- pushes the new system prompt to Langfuse (new version)
- writes the new skill file to disk
- uploads the new eval cases to the Langfuse evaluation dataset
- appends an audit row (including the full skill text) to apply_history.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .._common import utc_now_iso

logger = logging.getLogger(__name__)

_HISTORY_PATH = Path("data/outputs/apply_history.json")

# Local file that backs the LangfusePromptDataset for system_prompt.
# LangfusePromptDataset.save() only calls create_prompt() on the remote side;
# it never updates the local file.  With sync_policy: local the next campaign
# load treats the local file as the source of truth, detects a hash-mismatch
# against the new Langfuse version, and pushes the old content back — making
# the reflection a no-op.  We therefore mirror every successful apply back to
# disk so the two sides stay in sync.
_SYSTEM_PROMPT_PATH = Path("data/campaign/prompts/system_prompt.json")


def commit_reflection(
    proposed_prompt: Any,
    proposed_skill: str,
    proposed_eval_cases: Any,
    reflection_id: str,
) -> tuple[list[dict], str, list[dict], list[dict]]:
    """Commit an approved reflection proposal to the live locations.

    Returns:
        system_prompt_messages  – list of {role, content} dicts  → system_prompt
        skill_text              – markdown string                 → skill_text
        new_eval_cases          – list of Langfuse item dicts     → eval_cases
        apply_history           – full updated audit log          → apply_history
    """
    messages = _extract_messages(proposed_prompt)

    # Keep the local prompt file in sync with what LangfusePromptDataset will
    # push to Langfuse (it only writes remotely).  Without this the next
    # campaign run's sync_policy: local would overwrite Langfuse back to v1.
    _SYSTEM_PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SYSTEM_PROMPT_PATH.write_text(json.dumps(messages, indent=2), encoding="utf-8")
    logger.info(
        "apply %s: wrote updated system prompt to %s",
        reflection_id,
        _SYSTEM_PROMPT_PATH,
    )

    new_eval_cases = [
        {
            "id": item.id,
            "input": item.input,
            "expected_output": item.expected_output,
        }
        for item in proposed_eval_cases.items
    ]

    audit_row = {
        "reflection_id": reflection_id,
        "applied_at": utc_now_iso(),
        "new_prompt_messages": messages,
        "new_skill_text": proposed_skill,
        "new_eval_case_ids": [ec["id"] for ec in new_eval_cases],
    }

    history = _load_history()
    history.append(audit_row)

    logger.info(
        "apply %s: pushing new prompt (%d messages), skill (%d chars), "
        "%d new eval cases",
        reflection_id,
        len(messages),
        len(proposed_skill),
        len(new_eval_cases),
    )

    return messages, proposed_skill, new_eval_cases, history


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_messages(prompt: Any) -> list[dict]:
    """Convert proposed_prompt to a list of {role, content} dicts.

    The current catalog wiring (proposed_prompt: json.JSONDataset) always
    produces a plain list, so the isinstance branch is the only path reached
    today.  The ChatPromptTemplate fallback is defensive for a future catalog
    change (e.g. switching proposed_prompt to LangfusePromptDataset).
    """
    if isinstance(prompt, list):
        return [{"role": m["role"], "content": m["content"]} for m in prompt]
    # ChatPromptTemplate fallback
    messages = []
    for msg in prompt.messages:
        role = type(msg).__name__.replace("MessagePromptTemplate", "").lower()
        inner = getattr(msg, "prompt", None)
        template_str = getattr(inner, "template", None) or str(msg)
        messages.append({"role": role, "content": template_str})
    return messages


def _load_history() -> list[dict]:
    if _HISTORY_PATH.exists():
        return json.loads(_HISTORY_PATH.read_text())
    return []
