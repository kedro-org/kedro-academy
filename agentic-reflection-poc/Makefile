.PHONY: install seed test app viz reset run-cycle setup

PYTHON ?= .venv/bin/python
KEDRO ?= .venv/bin/kedro
STREAMLIT ?= .venv/bin/streamlit
PIP ?= .venv/bin/pip

install:
	/opt/miniconda3/bin/python3.12 -m venv .venv || python3 -m venv .venv
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

setup: install seed

seed:
	$(PYTHON) scripts/seed_synthetic_data.py

test:
	$(PYTHON) -m pytest -q

app:
	$(STREAMLIT) run src/agentic_reflection_poc/ui/app.py

viz:
	$(KEDRO) viz run

reset:
	rm -rf data/intermediate/* data/outputs/* data/reporting/* data/demo_state.json
	$(PYTHON) scripts/seed_synthetic_data.py

run-cycle:
	$(KEDRO) run --pipeline agent_run --params run_id=run_1
	$(KEDRO) run --pipeline evaluation --params run_id=run_1
	$(KEDRO) run --pipeline reflection --params run_id=run_1,proposal_id=proposal_1
	$(KEDRO) run --pipeline apply --params proposal_id=proposal_1
	$(KEDRO) run --pipeline agent_run --params run_id=run_2
	$(KEDRO) run --pipeline evaluation --params run_id=run_2
