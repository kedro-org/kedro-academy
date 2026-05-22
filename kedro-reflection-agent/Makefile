.PHONY: install seed test app viz reset run-cycle setup

UV        ?= uv
PYTHON    ?= uv run python
KEDRO     ?= uv run kedro
STREAMLIT ?= uv run streamlit

# ── setup ─────────────────────────────────────────────────────────────────────

## Install all deps (creates .venv automatically via uv sync)
install:
	$(UV) sync --extra dev

## Shortcut: install + seed in one go
setup: install seed

# ── seed / reset ──────────────────────────────────────────────────────────────

## Restore the v1 prompt, skill file, and eval cases; wipe all run outputs
seed:
	$(PYTHON) scripts/seed_demo.py

## Alias for seed (clearer intent when resetting mid-demo)
reset: seed

# ── run the app ───────────────────────────────────────────────────────────────

app:
	$(STREAMLIT) run app/main.py

viz:
	$(KEDRO) viz run

# ── tests ─────────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest -q

# ── full demo cycle (headless) ────────────────────────────────────────────────

## Run the complete three-step pipeline cycle without the UI
run-cycle:
	$(KEDRO) run --pipelines campaign    --params "run_id=run_1"
	$(KEDRO) run --pipelines evaluation  --params "run_id=run_1"
	$(KEDRO) run --pipelines reflection  --params "run_id=run_1,reflection_id=refl_1"
	$(KEDRO) run --pipelines apply       --params "reflection_id=refl_1"
	$(KEDRO) run --pipelines campaign    --params "run_id=run_2"
	$(KEDRO) run --pipelines evaluation  --params "run_id=run_2"
