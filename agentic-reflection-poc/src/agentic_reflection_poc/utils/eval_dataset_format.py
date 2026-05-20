"""Convert between POC eval cases and Langfuse dataset item format."""

from __future__ import annotations

from typing import Any


def to_langfuse_items(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map POC eval cases to LangfuseEvaluationDataset item schema (requires ``input``)."""
    items = []
    for case in cases:
        case_id = case["case_id"]
        items.append(
            {
                "id": case_id,
                "input": case,
                "expected_output": case.get("ground_truth"),
                "metadata": {
                    "is_regression": case.get("is_regression", False),
                    "source_failure_case_id": case.get("source_failure_case_id"),
                    "reason_added": case.get("reason_added"),
                },
            }
        )
    return items


def from_langfuse_items(items: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
    """Extract POC eval cases from Langfuse items or DatasetClient."""
    if hasattr(items, "items"):
        raw = items.items
        return [_item_to_case(it) for it in raw]
    return [_item_to_case(it) for it in items]


def _item_to_case(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        if "input" in item:
            return item["input"]
        return item
    if hasattr(item, "input"):
        payload = item.input
        if isinstance(payload, dict):
            return payload
    raise ValueError("Cannot parse Langfuse dataset item to eval case.")
