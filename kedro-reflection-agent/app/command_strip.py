"""Shared captions for Kedro command strips in the pipeline stage tabs.

Campaign allocates the *next* run_id; scouts / reflect operate on the latest
completed eval run (one id lower until that next run finishes).
"""


def caption_next_run(*, run_id: str, action: str, latest_run_id: str | None = None) -> str:
    """Caption for commands that create a new run directory."""
    latest = latest_run_id or "—"
    return f"Next run — {action} ({run_id}) · latest completed: {latest}"


def caption_active_run(*, run_id: str | None, action: str) -> str:
    """Caption for commands that target the latest completed eval run."""
    rid = run_id or "run_1"
    return f"Latest completed eval run ({rid}) — {action}"


def caption_apply(*, run_id: str | None, reflection_id: str) -> str:
    """Caption for the apply pipeline (writes config, no new run directory)."""
    rid = run_id or "run_1"
    return (
        f"Applies {reflection_id} from latest completed eval run ({rid}) — "
        "updates prompt/skill (no new run)"
    )
