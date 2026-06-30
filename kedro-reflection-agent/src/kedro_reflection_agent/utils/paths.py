"""Shared filesystem paths for cross-run output artifacts.

Paths are relative to the Kedro project root. Catalog YAML must keep the same
strings (see conf/base/catalog_apply.yml); Python code should import from here.
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path("data")
OUTPUTS_DIR = DATA_DIR / "outputs"

APPLY_HISTORY_PATH = OUTPUTS_DIR / "apply_history.json"
RUN_INDEX_PATH = OUTPUTS_DIR / "run_index.json"
SIGNAL_INDEX_PATH = OUTPUTS_DIR / "signal_index.json"
