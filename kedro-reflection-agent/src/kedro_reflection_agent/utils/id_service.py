"""ID service — single source of truth for all entity IDs.

Every ID in the system is generated or validated here. No other module
constructs IDs from scratch.

Canonical ID formats
────────────────────
  case_id          : "case_001", "case_002", ...
  run_id           : "run_1", "run_2", ...
  reflection_id    : "refl_1", "refl_2", ...
  dataset_item_id  : deterministic UUID5 derived from (agent_id, case_id)

The Langfuse problem — why deterministic UUIDs
──────────────────────────────────────────────
Langfuse assigns server-side UUIDs to dataset items.  When we sync local
eval_cases.json to Langfuse, the UUID we get back differs from our logical
"case_001".  Every piece of code then has to patch the two together with
``(metadata.case_id or item.id)`` hacks.

``dataset_item_id(agent_id, case_id)`` solves this by producing a UUID that
is *always the same* for a given (agent_id, case_id) pair — before and after
Langfuse sync, across resets, across machines.  We pass this UUID when
creating Langfuse items, so ``item.id`` IS our canonical key everywhere:
eval_cases.json, Langfuse, email filenames, scores, signals.

No metadata fallback.  No UUID-preservation logic in seed scripts.

Usage
─────
  from kedro_reflection_agent.utils.id_service import case_id, dataset_item_id

  cid  = case_id(1)                          # "case_001"
  uuid = dataset_item_id("b2b_sales", cid)   # always the same UUID
"""

from __future__ import annotations

import uuid

# ── Project namespace ─────────────────────────────────────────────────────────
# Derived once from the project name — never changes.
# All entity UUIDs are UUID5 children of this namespace.
_PROJECT_NS: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "kedro-reflection-agent")


# ── Generators ────────────────────────────────────────────────────────────────

def case_id(seq: int) -> str:
    """Return the canonical case ID for sequence number ``seq``.

    >>> case_id(1)
    'case_001'
    >>> case_id(20)
    'case_020'
    """
    return f"case_{seq:03d}"


def dataset_item_id(agent_id: str, case_id_str: str) -> str:
    """Return a deterministic UUID for a Langfuse dataset item.

    The UUID is stable: same inputs → same UUID, always.  Pass this as the
    ``id`` argument when creating Langfuse dataset items so that ``item.id``
    equals the value stored in eval_cases.json without any reconciliation.

    >>> dataset_item_id("b2b_sales", "case_001")   # same value every time
    '3f2504e0-...'
    """
    return str(uuid.uuid5(_PROJECT_NS, f"dataset_item:{agent_id}:{case_id_str}"))


def run_id(seq: int) -> str:
    """Return the canonical run ID for sequence number ``seq``.

    >>> run_id(1)
    'run_1'
    """
    return f"run_{seq}"


def reflection_id(seq: int) -> str:
    """Return the canonical reflection ID for sequence number ``seq``.

    >>> reflection_id(1)
    'refl_1'
    """
    return f"refl_{seq}"


# ── Validators ────────────────────────────────────────────────────────────────

def is_dataset_item_id(value: str) -> bool:
    """Return True if ``value`` looks like a UUID (Langfuse item ID)."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def is_case_id(value: str) -> bool:
    """Return True if ``value`` is a canonical case_XXX logical ID."""
    return value.startswith("case_") and value[5:].isdigit()


def resolve_case_id(item_id: str, metadata: dict | None) -> str:
    """Return the logical case_id for a Langfuse dataset item.

    Priority:
      1. ``metadata["case_id"]`` — set by seed scripts on every item
      2. ``item_id`` itself if it already looks like a case_id ("case_001")
      3. ``item_id`` as-is (UUID fallback — should not happen with this service)
    """
    if metadata:
        found = metadata.get("case_id", "")
        if found:
            return found
    if is_case_id(item_id):
        return item_id
    return item_id
