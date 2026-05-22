"""Fetch Langfuse analytics via public API (daily metrics + metrics v1)."""

from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

CAMPAIGN_TRACE_NAME = "campaign_email_generation"
CASE_SCORE_NAME = "case_total"


def basic_auth_header(credentials: dict[str, Any]) -> str:
    raw = f"{credentials['public_key']}:{credentials['secret_key']}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _api_get(credentials: dict[str, Any], path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    host = (credentials.get("host") or "https://cloud.langfuse.com").rstrip("/")
    url = f"{host}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": basic_auth_header(credentials), "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        logger.warning("Langfuse API %s failed: %s %s", path, exc.code, body)
        raise
    except urllib.error.URLError as exc:
        logger.warning("Langfuse API %s unreachable: %s", path, exc)
        raise


def fetch_daily_metrics(
    credentials: dict[str, Any],
    *,
    trace_name: str = CAMPAIGN_TRACE_NAME,
    days: int = 14,
) -> list[dict[str, Any]]:
    """Daily trace/observation counts and cost."""
    try:
        payload = _api_get(
            credentials,
            "/api/public/metrics/daily",
            {"traceName": trace_name, "limit": str(days)},
        )
        return payload.get("data", [])
    except Exception:  # noqa: BLE001
        return []


def fetch_trace_count_timeseries(
    credentials: dict[str, Any],
    *,
    trace_name: str = CAMPAIGN_TRACE_NAME,
    days: int = 14,
) -> list[dict[str, Any]]:
    """Trace counts grouped by day (Metrics API v1)."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    query = {
        "view": "traces",
        "metrics": [{"measure": "count", "aggregation": "count"}],
        "dimensions": [],
        "filters": [{"column": "name", "operator": "=", "value": trace_name, "type": "string"}],
        "timeDimension": {"granularity": "day"},
        "fromTimestamp": start.strftime("%Y-%m-%dT00:00:00Z"),
        "toTimestamp": end.strftime("%Y-%m-%dT23:59:59Z"),
    }
    try:
        payload = _api_get(
            credentials,
            "/api/public/metrics",
            {"query": json.dumps(query)},
        )
        return payload.get("data", [])
    except Exception:  # noqa: BLE001
        return []


def fetch_case_score_timeseries(
    credentials: dict[str, Any],
    *,
    score_name: str = CASE_SCORE_NAME,
    days: int = 14,
) -> list[dict[str, Any]]:
    """Average case_total score by day."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    query = {
        "view": "scores-numeric",
        "metrics": [{"measure": "value", "aggregation": "avg"}],
        "dimensions": [],
        "filters": [{"column": "name", "operator": "=", "value": score_name, "type": "string"}],
        "timeDimension": {"granularity": "day"},
        "fromTimestamp": start.strftime("%Y-%m-%dT00:00:00Z"),
        "toTimestamp": end.strftime("%Y-%m-%dT23:59:59Z"),
    }
    try:
        payload = _api_get(
            credentials,
            "/api/public/metrics",
            {"query": json.dumps(query)},
        )
        return payload.get("data", [])
    except Exception:  # noqa: BLE001
        return []
