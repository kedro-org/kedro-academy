.PHONY: install seed test app viz reset run-cycle setup

PYTHON   ?= .venv/bin/python
KEDRO    ?= .venv/bin/kedro
STREAMLIT ?= .venv/bin/streamlit
PIP      ?= .venv/bin/pip

# ── setup ─────────────────────────────────────────────────────────────────────

install:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

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
