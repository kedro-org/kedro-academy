"""End-to-end scenarios for OpikEvaluationDataset — intent detection domain.

Manual end-to-end test script for ``OpikEvaluationDataset``. Run top-to-bottom
and verify results in the **Opik UI** after each section.

**Prerequisites:**
- Opik credentials in ``conf/local/credentials.yml`` under ``opik_credentials``
- ``opik`` and ``kedro-datasets[opik-opikevaluationdataset]`` installed
- ``OPENAI_API_KEY`` exported in the environment (Scenario 11 only)

---

Table of contents
-----------------

| Section | Scenarios | What it covers |
|---------|-----------|----------------|
| **1. Local mode** | 1–4 | Fresh start, idempotent reload, incremental sync, ``save()`` with local merge |
| **2. Remote mode** | 5–6 | Remote load, ``save()`` without local file interaction |
| **3. UUID id behaviour** | 7–8 | UUID ids forwarded to Opik; non-UUID ids stripped |
| **4. Edge cases** | 9–10 | Items without id, invalid credentials |
| **5. Lifecycle & integration** | 11–12 | Native Opik API operations, running an experiment |
"""

import sys
from pathlib import Path

# Add src/ to the path so the script works when run directly
# (e.g. `python src/kedro_agentic_workflows/pipelines/.../e2e_example.py`)
sys.path.insert(0, str(Path(__file__).parents[3]))

import json
import logging
import os
import tempfile
import time
from datetime import datetime

import yaml
from kedro.io import DatasetError
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult

from kedro_agentic_workflows.datasets.opik_evaluation_dataset import OpikEvaluationDataset


def _uuid7() -> str:
    """Generate a UUID version 7 (time-ordered random).

    UUID v7 is required by the Opik cloud API for dataset item IDs.
    Compatible with Python < 3.13 which does not have uuid.uuid7().
    """
    timestamp_ms = int(time.time() * 1000)
    rand = int.from_bytes(os.urandom(10), "big")
    rand_a = (rand >> 62) & 0xFFF          # 12 random bits after version nibble
    rand_b = rand & 0x3FFFFFFFFFFFFFFF     # 62 random bits after variant bits
    uuid_int = (
        (timestamp_ms & 0xFFFFFFFFFFFF) << 80
        | 0x7 << 76
        | rand_a << 64
        | 0b10 << 62
        | rand_b
    )
    h = f"{uuid_int:032x}"
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s — %(levelname)s — %(message)s",
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

CREDENTIALS_FILE = Path("conf/local/credentials.yml")
with open(CREDENTIALS_FILE) as f:
    all_credentials = yaml.safe_load(f)

CREDENTIALS = {
    "api_key": all_credentials["opik_credentials"]["api_key"],
    "workspace": all_credentials["opik_credentials"].get("workspace", ""),
}

RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")
DATASET_NAME = f"e2e-intent-eval-{RUN_ID}"

TMP_DIR = Path(tempfile.mkdtemp(prefix="e2e_opik_"))
LOCAL_FILE = TMP_DIR / "intent_eval_items.json"

print(f"Dataset name : {DATASET_NAME}")
print(f"Local file   : {LOCAL_FILE}")

# ---------------------------------------------------------------------------
# Test data
#
# UUIDs are used so that remote rows have stable identities and
# assertions on id values are possible. Items with human-readable ids
# are used only in Scenarios 7–8 to exercise the id-stripping path.
# ---------------------------------------------------------------------------

# Stable UUID v7 values generated once per run for the main intent items.
# Opik requires UUID v7 for dataset item IDs.
_UUID_1 = _uuid7()
_UUID_2 = _uuid7()
_UUID_3 = _uuid7()
_UUID_4 = _uuid7()
_UUID_5 = _uuid7()
_UUID_6 = _uuid7()

INITIAL_ITEMS = [
    {
        "id": _UUID_1,
        "input": {"question": "How do I submit a claim for a car accident?"},
        "expected_output": {"intent": "general_question"},
    },
    {
        "id": _UUID_2,
        "input": {"question": "My car was hit in the parking lot, the door is damaged."},
        "expected_output": {"intent": "claim_new"},
    },
    {
        "id": _UUID_3,
        "input": {"question": "What's the status of my claim 48392?"},
        "expected_output": {"intent": "existing_claim_question"},
    },
]

# New item added in Scenario 3
NEW_ITEM = {
    "id": _UUID_4,
    "input": {"question": "I need to upload more documents to my claim."},
    "expected_output": {"intent": "existing_claim_question"},
}

# Items passed to save() in Scenario 4:
#   _UUID_5, _UUID_6 — new
#   _UUID_1           — same UUID, updated expected_output
#                       (new content hash → new remote row; local file merges by id)
SAVE_ITEMS = [
    {
        "id": _UUID_5,
        "input": {"question": "I lost my phone during my trip yesterday."},
        "expected_output": {"intent": "claim_new"},
    },
    {
        "id": _UUID_6,
        "input": {"question": "I need help."},
        "expected_output": {"intent": "clarification_needed"},
    },
    {
        "id": _UUID_1,
        "input": {"question": "How do I submit a claim for a car accident?"},
        "expected_output": {"intent": "general_question_updated"},
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_local(items: list[dict]) -> None:
    """Write items to the local JSON test file."""
    LOCAL_FILE.write_text(json.dumps(items, indent=2))
    print(f"  Wrote {len(items)} item(s) to local file")


def read_local() -> list[dict]:
    """Read items from the local JSON test file."""
    return json.loads(LOCAL_FILE.read_text())


def make_dataset(sync_policy: str = "local", filepath: str | None = None) -> OpikEvaluationDataset:
    """Create an ``OpikEvaluationDataset`` instance with the shared test config."""
    return OpikEvaluationDataset(
        dataset_name=DATASET_NAME,
        credentials=CREDENTIALS,
        filepath=filepath if filepath is not None else str(LOCAL_FILE),
        sync_policy=sync_policy,
    )


def summarise_remote(opik_dataset) -> dict:
    """Return a summary dict of the remote dataset for inspection."""
    items = opik_dataset.get_items()
    return {
        "count": len(items),
        "ids": sorted(item["id"] for item in items),
    }


# ---------------------------------------------------------------------------
# Section 1: Local mode (Scenarios 1–4)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("SECTION 1: LOCAL MODE")
print("=" * 60)

# --- Scenario 1: Fresh start ------------------------------------------------

print("\n" + "=" * 60)
print("SCENARIO 1: Fresh start — create remote dataset + sync local items")
print("=" * 60)
print("""
Steps:
  1. Write 3 items with UUID ids to the local file.
  2. Call load() with sync_policy='local'.

Expected:
  - Remote dataset is created (did not exist before).
  - All 3 local items are inserted to remote.
  - load() returns an opik.Dataset with 3 items.

Expected logs:
  Dataset '...' not found on Opik, creating it.
  Syncing 3 item(s) from '...' to remote dataset '...'.
  Loaded dataset '...' (sync_policy='local').

Verify in Opik UI:
  - Dataset exists under Datasets.
  - Contains 3 items with the correct input/expected_output.
""")

write_local(INITIAL_ITEMS)

ds = make_dataset()
result1 = ds.load()

summary1 = summarise_remote(result1)
assert summary1["count"] == 3, f"Expected 3 items, got {summary1['count']}"
assert _UUID_1 in summary1["ids"], f"UUID_1 not found in remote: {summary1['ids']}"
assert _UUID_2 in summary1["ids"], f"UUID_2 not found in remote: {summary1['ids']}"
assert _UUID_3 in summary1["ids"], f"UUID_3 not found in remote: {summary1['ids']}"

print(f"\n✓ PASSED — Remote has {summary1['count']} item(s): {summary1['ids']}")

# --- Scenario 2: Idempotent reload ------------------------------------------

print("\n" + "=" * 60)
print("SCENARIO 2: Idempotent reload — no duplicates on repeated load()")
print("=" * 60)
print("""
Steps:
  1. Load the same dataset again (new instance, same config).
  2. Local file has not changed — same content hashes.

Expected:
  - Opik SDK deduplicates by content hash: no new remote rows.
  - Remote item count remains 3.

Verify in Opik UI:
  - Dataset still shows 3 items (not 6).
""")

ds2 = make_dataset()
result2 = ds2.load()

summary2 = summarise_remote(result2)
assert summary2["count"] == 3, f"Expected 3 items (no duplicates), got {summary2['count']}"
assert summary2["ids"] == summary1["ids"], (
    f"Ids changed between loads: before={summary1['ids']}, after={summary2['ids']}"
)

print(f"\n✓ PASSED — Still {summary2['count']} item(s) (no duplicates)")

# --- Scenario 3: Incremental sync -------------------------------------------

print("\n" + "=" * 60)
print("SCENARIO 3: Incremental sync — one new local item")
print("=" * 60)
print("""
Steps:
  1. Append a new item (UUID_4) to the local file.
  2. Call load().

Expected:
  - Remote gains exactly 1 new item (UUID_4).
  - Existing 3 items are not duplicated (content-hash dedup).
  - Original items are unchanged on remote.

Verify in Opik UI:
  - Dataset now shows 4 items.
""")

write_local(INITIAL_ITEMS + [NEW_ITEM])

ds3 = make_dataset()
result3 = ds3.load()

summary3 = summarise_remote(result3)
assert summary3["count"] == 4, f"Expected 4 items, got {summary3['count']}"
assert _UUID_4 in summary3["ids"], f"UUID_4 not found on remote: {summary3['ids']}"

items3 = result3.get_items()
item_uuid1 = next((i for i in items3 if i["id"] == _UUID_1), None)
assert item_uuid1 is not None, "UUID_1 not found in remote items"
assert item_uuid1["input"]["question"] == INITIAL_ITEMS[0]["input"]["question"], (
    f"UUID_1 content changed unexpectedly: {item_uuid1['input']}"
)

print(f"\n✓ PASSED — {summary3['count']} item(s): {summary3['ids']}")

# --- Scenario 4: save() with local merge ------------------------------------

print("\n" + "=" * 60)
print("SCENARIO 4: save() — insert to remote + merge into local file")
print("=" * 60)
print("""
Steps:
  1. Call save() with 3 items: UUID_5 (new), UUID_6 (new),
     UUID_1 (same UUID, updated expected_output).

Expected (remote):
  - 2 new rows for UUID_5 and UUID_6.
  - UUID_1 with new expected_output creates a new remote row
    (content-hash differs from old content → Opik adds a row).
  - Remote total: 4 existing + 3 saved = up to 7 rows
    (exact count depends on Opik content-hash dedup for UUID_1).

Expected (local file):
  - UUID_5 and UUID_6 appended.
  - UUID_1 entry updated in place (local merge by id).
  - Local total: 6 items (4 existing + 2 new; UUID_1 replaced in place).

Verify in Opik UI:
  - Local file on disk has 6 items with UUID_1's expected_output updated.
""")

ds4 = make_dataset()
ds4.save(SAVE_ITEMS)

local_items4 = read_local()
local_ids4 = [i.get("id") for i in local_items4]

assert len(local_items4) == 6, f"Expected 6 local items, got {len(local_items4)}"
assert _UUID_5 in local_ids4, "UUID_5 not found in local file"
assert _UUID_6 in local_ids4, "UUID_6 not found in local file"

item_uuid1_local = next((i for i in local_items4 if i.get("id") == _UUID_1), None)
assert item_uuid1_local is not None, "UUID_1 not found in local file after save()"
assert item_uuid1_local["expected_output"]["intent"] == "general_question_updated", (
    f"UUID_1 expected_output not updated locally: {item_uuid1_local['expected_output']}"
)

print(f"\n✓ PASSED — Local file has {len(local_items4)} item(s); UUID_1 updated in place")
print("  (Check Opik UI for remote item count — UUID_1 new content creates an additional row)")

# ---------------------------------------------------------------------------
# Section 2: Remote mode (Scenarios 5–6)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("SECTION 2: REMOTE MODE")
print("=" * 60)

# --- Scenario 5: Remote load from existing dataset --------------------------

print("\n" + "=" * 60)
print("SCENARIO 5: Remote mode — load from existing dataset")
print("=" * 60)
print("""
Steps:
  1. Instantiate OpikEvaluationDataset with sync_policy='remote'.
  2. Call load().

Expected:
  - Remote dataset is fetched as-is.
  - Local file is NOT read or modified.
  - load() returns the opik.Dataset with all remote items.

Verify in Opik UI:
  - No new items created; dataset unchanged.
""")

ds5 = make_dataset(sync_policy="remote")
result5 = ds5.load()

summary5 = summarise_remote(result5)
assert summary5["count"] >= 4, (
    f"Expected at least 4 items from prior scenarios, got {summary5['count']}"
)
assert _UUID_2 in summary5["ids"], f"UUID_2 not found in remote after remote load: {summary5['ids']}"

items5 = result5.get_items()
item_uuid2 = next((i for i in items5 if i["id"] == _UUID_2), None)
assert item_uuid2 is not None, "UUID_2 not found in remote items"
assert item_uuid2["input"]["question"] == INITIAL_ITEMS[1]["input"]["question"], (
    f"UUID_2 content changed unexpectedly: {item_uuid2['input']}"
)

print(f"\n✓ PASSED — Remote mode loaded {summary5['count']} item(s)")

# --- Scenario 6: Remote save() — uploads to remote only --------------------

print("\n" + "=" * 60)
print("SCENARIO 6: Remote mode — save() uploads to remote, local file untouched")
print("=" * 60)
print("""
Steps:
  1. Record local file item count before save().
  2. Call save() with a new item using sync_policy='remote'.

Expected:
  - New item is uploaded to remote.
  - Local file is NOT modified (still has same items as after Scenario 4).

Verify in Opik UI:
  - Remote dataset has one additional item.
""")

local_items_before = read_local()
local_count_before = len(local_items_before)

remote_save_item = {
    "id": _uuid7(),
    "input": {"question": "Can I update my contact address in my insurance profile?"},
    "expected_output": {"intent": "general_question"},
}

ds6 = make_dataset(sync_policy="remote")
ds6.save([remote_save_item])

local_items_after = read_local()
assert len(local_items_after) == local_count_before, (
    f"Local file was modified in remote mode: before={local_count_before}, "
    f"after={len(local_items_after)}"
)
assert not any(i.get("id") == remote_save_item["id"] for i in local_items_after), (
    "Remote-only save() item found in local file — should not be written locally"
)

print(f"\n✓ PASSED — Local file unchanged ({local_count_before} items); "
      "remote received the new item")

# ---------------------------------------------------------------------------
# Section 3: UUID id behaviour (Scenarios 7–8)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("SECTION 3: UUID ID BEHAVIOUR (Opik-specific)")
print("=" * 60)

# --- Scenario 7: UUID ids preserved; non-UUID ids stripped ------------------

print("\n" + "=" * 60)
print("SCENARIO 7: UUID ids forwarded; human-readable ids stripped")
print("=" * 60)
print("""
Steps:
  1. Create a separate dataset (fresh name) with one UUID-id item
     and one human-readable-id item.
  2. Call load() with sync_policy='local'.

Expected:
  - UUID-id item appears on remote with its original UUID.
  - Human-readable-id item appears with an auto-generated UUID
    (the original 'human_001' id is not present in any remote item).

Verify in Opik UI:
  - One remote item has id == UUID_id_item's UUID.
  - The other remote item has a system-generated UUID (not 'human_001').
""")

uuid_id_item = {
    "id": _uuid7(),
    "input": {"question": "UUID-id item — stable remote identity."},
    "expected_output": {"intent": "test"},
}
non_uuid_id_item = {
    "id": "human_001",
    "input": {"question": "Human-readable id item — id will be stripped."},
    "expected_output": {"intent": "test"},
}

tmp_file7 = TMP_DIR / "scenario7.json"
tmp_file7.write_text(json.dumps([uuid_id_item, non_uuid_id_item], indent=2))

ds7 = OpikEvaluationDataset(
    dataset_name=f"{DATASET_NAME}-sc7",
    credentials=CREDENTIALS,
    filepath=str(tmp_file7),
    sync_policy="local",
)
result7 = ds7.load()

items7 = result7.get_items()
assert len(items7) == 2, f"Expected 2 remote items, got {len(items7)}"

remote_ids7 = [i["id"] for i in items7]
assert uuid_id_item["id"] in remote_ids7, (
    f"UUID id not found in remote: {remote_ids7}"
)
assert "human_001" not in remote_ids7, (
    f"Human-readable id leaked to remote: {remote_ids7}"
)

print(f"\n✓ PASSED — UUID id preserved; 'human_001' stripped (remote ids: {remote_ids7})")

# --- Scenario 8: Same UUID, changed content — UUID still forwarded ----------

print("\n" + "=" * 60)
print("SCENARIO 8: Same UUID id with changed content — id still forwarded")
print("=" * 60)
print("""
Steps:
  1. Update the UUID-id item's expected_output in the local file.
  2. Call load() again.

Expected:
  - The UUID is still forwarded in the insert call (not stripped).
  - Opik receives the item with the same UUID id.
  - Remote may contain both the old and the new row (content-hash differs).

Note:
  Whether Opik replaces or appends the row depends on its server-side
  behaviour for duplicate UUIDs. The dataset guarantees the UUID is
  forwarded; it does not guarantee server-side upsert semantics.
""")

updated_uuid_item = {
    **uuid_id_item,
    "expected_output": {"intent": "test_updated"},
}
tmp_file7.write_text(json.dumps([updated_uuid_item, non_uuid_id_item], indent=2))

ds8 = OpikEvaluationDataset(
    dataset_name=f"{DATASET_NAME}-sc7",
    credentials=CREDENTIALS,
    filepath=str(tmp_file7),
    sync_policy="local",
)
result8 = ds8.load()

items8 = result8.get_items()
remote_ids8 = [i["id"] for i in items8]
assert uuid_id_item["id"] in remote_ids8, (
    f"UUID id no longer in remote after content change: {remote_ids8}"
)

print(f"\n✓ PASSED — UUID id still present after content change (remote ids: {remote_ids8})")

# ---------------------------------------------------------------------------
# Section 4: Edge cases (Scenarios 9–10)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("SECTION 4: EDGE CASES")
print("=" * 60)

# --- Scenario 9: Items without id — warning + new row on every sync ---------

print("\n" + "=" * 60)
print("SCENARIO 9: Items without id — warning emitted, new row on every load()")
print("=" * 60)
print("""
Steps:
  1. Write 2 items with no 'id' field to a local file.
  2. Call load() twice.

Expected:
  - Warning is logged on each load about missing/empty 'id' fields.
  - Each load() re-inserts the items with new auto-generated UUIDs.
  - Remote row count grows by 2 on the second load (no dedup possible
    without content-hash match — same content IS deduped; different
    content would grow).

Note:
  Because content is unchanged, Opik content-hash dedup DOES prevent
  duplicates here. Remote count should stay at 2 after the second load.
  Items without id that change content will grow unbounded.
""")

no_id_items = [
    {"input": {"question": "What happens without an id?"}},
    {"input": {"question": "Another item with no id."}},
]
tmp_file9 = TMP_DIR / "scenario9.json"
tmp_file9.write_text(json.dumps(no_id_items, indent=2))

ds9a = OpikEvaluationDataset(
    dataset_name=f"{DATASET_NAME}-sc9",
    credentials=CREDENTIALS,
    filepath=str(tmp_file9),
    sync_policy="local",
)
result9a = ds9a.load()
count9a = len(result9a.get_items())
assert count9a == 2, f"Expected 2 items after first load, got {count9a}"

ds9b = OpikEvaluationDataset(
    dataset_name=f"{DATASET_NAME}-sc9",
    credentials=CREDENTIALS,
    filepath=str(tmp_file9),
    sync_policy="local",
)
result9b = ds9b.load()
count9b = len(result9b.get_items())

# Content unchanged → content-hash dedup → count stays at 2
assert count9b == 2, (
    f"Expected 2 items after second load (content-hash dedup), got {count9b}"
)

print(f"\n✓ PASSED — {count9b} item(s) on remote; content-hash dedup prevented "
      "duplicates for unchanged items")
print("  (Check logs above for 'missing, None, or empty id' warning)")

# --- Scenario 10: Invalid credentials raise DatasetError --------------------

print("\n" + "=" * 60)
print("SCENARIO 10: Invalid credentials — DatasetError raised")
print("=" * 60)
print("""
Steps:
  1. Attempt to create OpikEvaluationDataset instances with bad configs.

Expected:
  - Missing api_key → DatasetError at __init__
  - Empty api_key  → DatasetError at __init__
""")

test_cases_10 = [
    {
        "label": "Missing api_key",
        "credentials": {"workspace": "x"},
        "expect_in_error": "api_key",
    },
    {
        "label": "Empty api_key",
        "credentials": {"api_key": "   "},
        "expect_in_error": "api_key",
    },
]

for tc in test_cases_10:
    try:
        OpikEvaluationDataset(
            dataset_name="dummy",
            credentials=tc["credentials"],
        )
        print(f"  ✗ {tc['label']}: should have raised DatasetError")
        assert False, f"Expected DatasetError for: {tc['label']}"
    except DatasetError as e:
        assert tc["expect_in_error"] in str(e), (
            f"Error message for '{tc['label']}' should mention '{tc['expect_in_error']}': {e}"
        )
        print(f"  ✓ {tc['label']}: DatasetError raised as expected")

print("\n✓ PASSED — All invalid config cases raise DatasetError")

# ---------------------------------------------------------------------------
# Section 5: Lifecycle & integration (Scenarios 11–12)
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("SECTION 5: LIFECYCLE & INTEGRATION")
print("=" * 60)

# --- Scenario 11: Native Opik API — update and delete ----------------------

print("\n" + "=" * 60)
print("SCENARIO 11: Lifecycle via native Opik API — update and delete")
print("=" * 60)
print("""
Steps:
  1. Load the main dataset (built by Scenarios 1–4).
  2. Update the first item's expected_output via dataset.update().
  3. Delete the last item via dataset.delete().

Expected:
  - Updated item reflects new expected_output.
  - Deleted item no longer present in get_items().

Verify in Opik UI:
  - Correct item has updated expected_output.
  - Deleted item is gone.
""")

ds11 = make_dataset(sync_policy="remote")
result11 = ds11.load()
items11_before = result11.get_items()
count11_before = len(items11_before)

assert count11_before >= 2, f"Need at least 2 items for update/delete demo, got {count11_before}"

# Update first item
to_update = {**items11_before[0], "expected_output": {"intent": "lifecycle_updated"}}
result11.update([to_update])

refreshed11 = result11.get_items()
updated_item = next((i for i in refreshed11 if i["id"] == items11_before[0]["id"]), None)
assert updated_item is not None, "Updated item not found after update()"
assert updated_item["expected_output"]["intent"] == "lifecycle_updated", (
    f"Update did not take effect: {updated_item['expected_output']}"
)

# Delete last item
to_delete_id = items11_before[-1]["id"]
result11.delete([to_delete_id])

refreshed11_after_delete = result11.get_items()
deleted_ids = [i["id"] for i in refreshed11_after_delete]
assert to_delete_id not in deleted_ids, (
    f"Deleted item {to_delete_id} still present in remote"
)

print(f"\n✓ PASSED — Item {items11_before[0]['id']} updated; "
      f"item {to_delete_id} deleted")
print(f"  Items remaining: {len(refreshed11_after_delete)}")

# --- Scenario 12: Running an experiment with evaluate() --------------------

print("\n" + "=" * 60)
print("SCENARIO 12: Running an experiment with opik.evaluation.evaluate()")
print("=" * 60)
print("""
Steps:
  1. Load the main dataset.
  2. Define a simple echo task and an exact-match scorer.
  3. Run opik.evaluation.evaluate().

Expected:
  - Experiment is created in Opik.
  - Scores are computed for each item.
  - experiment_url is printed.

Note: Requires OPENAI_API_KEY (used only for the LLM judge in the full
pipeline — the simple echo task used here does not need it).

Verify in Opik UI:
  - Experiment appears under the dataset.
  - Each item has a score.
""")


def echo_task(dataset_item: dict) -> dict:
    """Return the expected_output as the task output (trivial echo)."""
    return {"output": dataset_item.get("expected_output", {})}


def exact_match_scorer(dataset_item: dict, task_outputs: dict, **kwargs) -> ScoreResult:
    """Score 1.0 if task output matches expected_output, else 0.0."""
    expected = dataset_item.get("expected_output", {})
    actual = task_outputs.get("output", {})
    score = 1.0 if actual == expected else 0.0
    return ScoreResult(
        name="exact_match",
        value=score,
        reason=f"expected={expected}, actual={actual}",
    )


ds12 = make_dataset(sync_policy="remote")
eval_dataset = ds12.load()

experiment_name = f"e2e-echo-experiment-{RUN_ID}"
result12 = evaluate(
    dataset=eval_dataset,
    task=echo_task,
    scoring_functions=[exact_match_scorer],
    experiment_name=experiment_name,
    experiment_config={"task": "echo", "scorer": "exact_match"},
)

scores12 = [
    sr.value
    for tr in result12.test_results
    for sr in tr.score_results
    if not sr.scoring_failed
]
assert len(scores12) > 0, "No scores recorded — check that the dataset has items"

avg12 = sum(scores12) / len(scores12)
print(f"\n✓ PASSED — Experiment '{experiment_name}' completed")
print(f"  Items scored: {len(scores12)}")
print(f"  Average exact_match score: {avg12:.2f}")
print(f"  Results: {result12.experiment_url}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("ALL SCENARIOS PASSED")
print("=" * 60)
print(f"Dataset: {DATASET_NAME}")
print(f"Local temp dir: {TMP_DIR}")
print("\nClean up:")
print(f"  - Delete dataset '{DATASET_NAME}' from the Opik UI")
print(f"  - Delete auxiliary datasets '{DATASET_NAME}-sc7' and '{DATASET_NAME}-sc9'")
