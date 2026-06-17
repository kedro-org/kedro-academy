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

## Restore v1 prompts, skills, eval cases and targets; wipe all run outputs (all agents)
## Pass N=<number> to seed only the first N cases, e.g. make seed N=3
seed:
	$(PYTHON) scripts/seed_demo.py $(if $(N),--cases $(N),)

## Alias for seed (clearer intent when resetting mid-demo)
reset: seed

# ── run the app ───────────────────────────────────────────────────────────────

app:
	$(STREAMLIT) run app/main.py

viz:
	$(KEDRO) viz run --params agent_id=$(agent)


# ── full demo cycle (headless) ────────────────────────────────────────────────

## Run the complete three-step pipeline cycle without the UI
## Pass agent=<agent_id> to target a specific agent, e.g. make run-cycle agent=b2b_sales
agent ?= b2b_sales
run-cycle:
	$(KEDRO) run --pipelines campaign    --params=agent_id=$(agent),run_id=run_1
	$(KEDRO) run --pipelines evaluation  --params=agent_id=$(agent),run_id=run_1
	$(KEDRO) run --pipelines scouts      --params=agent_id=$(agent),run_id=run_1
	$(KEDRO) run --pipelines reflection  --params=agent_id=$(agent),run_id=run_1,reflection_id=refl_1
	$(KEDRO) run --pipelines apply       --params=agent_id=$(agent),reflection_id=refl_1
	$(KEDRO) run --pipelines campaign    --params=agent_id=$(agent),run_id=run_2
	$(KEDRO) run --pipelines evaluation  --params=agent_id=$(agent),run_id=run_2
