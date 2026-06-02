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

from kedro_reflection_agent.pipelines._common import utc_now_iso

logger = logging.getLogger(__name__)

_HISTORY_PATH = Path("data/outputs/apply_history.json")

def commit_reflection(
    proposed_prompt: Any,
    proposed_skill: str,
    proposed_eval_cases: Any,
    reflection_id: str,
    agent_id: str,
) -> tuple[list[dict], str, list[dict], list[dict]]:
    """Commit an approved reflection proposal to the live locations.

    Returns:
        system_prompt_messages  – list of {role, content} dicts  → system_prompt
        skill_text              – markdown string                 → skill_text
        new_eval_cases          – list of Langfuse item dicts     → eval_cases
        apply_history           – full updated audit log          → apply_history
    """
    messages = _extract_messages(proposed_prompt)

    prompts_dir = Path("data") / agent_id / "campaign" / "prompts"
    skills_dir = Path("data") / agent_id / "campaign" / "skills"

    # Archive the current active files before overwriting, so each apply cycle
    # leaves a numbered snapshot: system_prompt_v1.json, system_prompt_v2.json, …
    # The archive number is the outgoing version (current file before this apply).
    prompt_version = _archive_file(
        prompts_dir / "system_prompt.json",
        json.dumps(messages, indent=2),
    )
    skill_version = _archive_file(
        skills_dir / f"{agent_id}_style.md",
        proposed_skill,
    )
    logger.info(
        "apply %s: archived prompt → v%d, skill → v%d; wrote new active files",
        reflection_id,
        prompt_version - 1,
        skill_version - 1,
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
        "agent_id": agent_id,
        "reflection_id": reflection_id,
        "applied_at": utc_now_iso(),
        "prompt_version": prompt_version,
        "skill_version": skill_version,
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


def _archive_file(active_path: Path, new_content: str) -> int:
    """Archive ``active_path`` as a numbered snapshot, then write ``new_content``.

    Snapshots are named ``<stem>_v{N}<suffix>`` alongside the active file.
    The function counts existing snapshots to determine the outgoing version
    number, archives the current content as v{N}, writes the new content as
    the active file, and returns the *new* version number (N + 1).

    On the very first apply:
      - v1 was written by seed_demo.py as the active file.
      - This archives it as ``system_prompt_v1.json`` / ``*_style_v1.md``.
      - The new proposed content becomes the active file (v2 in Langfuse terms).
    """
    active_path.parent.mkdir(parents=True, exist_ok=True)
    stem, suffix = active_path.stem, active_path.suffix

    existing = list(active_path.parent.glob(f"{stem}_v*{suffix}"))
    outgoing_version = len(existing) + 1

    if active_path.exists():
        archive_path = active_path.parent / f"{stem}_v{outgoing_version}{suffix}"
        archive_path.write_text(active_path.read_text(encoding="utf-8"), encoding="utf-8")

    active_path.write_text(new_content, encoding="utf-8")
    return outgoing_version + 1  # the version that just became active
