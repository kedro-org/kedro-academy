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

## Restore v1 prompts, skills, eval cases and targets; wipe all run outputs
## Pass N=<number> to seed only the first N cases, e.g. make seed N=3
## Pass AGENT=<agent_id> to seed a single agent, e.g. make seed AGENT=b2b_sales
seed:
	$(PYTHON) scripts/seed_demo.py $(if $(N),--cases $(N),) $(if $(AGENT),--agent $(AGENT),)

## Alias for seed (clearer intent when resetting mid-demo)
reset: seed

# ── run the app ───────────────────────────────────────────────────────────────

app:
	$(STREAMLIT) run app/main.py

viz:
	$(KEDRO) viz run


# ── full demo cycle (headless) ────────────────────────────────────────────────

## Run the complete three-step pipeline cycle without the UI
run-cycle:
	$(KEDRO) run --pipelines campaign    --params=agent_id=b2b_sales,run_id=run_1
	$(KEDRO) run --pipelines evaluation  --params=agent_id=b2b_sales,run_id=run_1
	$(KEDRO) run --pipelines scouts      --params=agent_id=b2b_sales,run_id=run_1
	$(KEDRO) run --pipelines reflection  --params=agent_id=b2b_sales,run_id=run_1,reflection_id=refl_1
	$(KEDRO) run --pipelines apply       --params=agent_id=b2b_sales,reflection_id=refl_1
	$(KEDRO) run --pipelines campaign    --params=agent_id=b2b_sales,run_id=run_2
	$(KEDRO) run --pipelines evaluation  --params=agent_id=b2b_sales,run_id=run_2
