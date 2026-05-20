# kedro-reflection-agent

A Kedro + Streamlit demo of an **agentic reflection / continuous learning** loop.

A B2B campaign agent generates personalised outreach emails for telco sales. After running on an eval set, a meta-agent reflects on the failures and proposes updates to the system prompt, the skill file, and the eval set itself. Re-running the agent against the new artifacts produces visibly better emails.

> Status: **scaffold only**. No node implementations yet. Pipelines and UI components are filled in slice by slice.

## Project shape

```
kedro-reflection-agent/
├── conf/                          # Kedro configs (one catalog_*.yml per pipeline)
├── data/
│   ├── seed/                      # synthetic customers + products
│   ├── agent_run/, evaluation/, reflection/   # pipeline inputs (prompts, skills)
│   └── outputs/                   # runs/{run_id}/ and reflections/{reflection_id}/
├── src/kedro_reflection_agent/
│   ├── data_models.py             # shared Pydantic models
│   ├── datasets/                  # project-specific datasets (if needed)
│   └── pipelines/{agent_run,evaluation,reflection,apply}/
├── app/                           # Streamlit dashboard
│   ├── main.py, runner.py, state.py
│   └── components/                # one file per demo step
└── tests/
```

Both halves share one venv. Streamlit invokes Kedro via subprocess (`kedro run -p <pipeline>`) and reads back from `data/outputs/`. Prompts, traces, and eval datasets live partly on disk and partly in Langfuse via the experimental `kedro-datasets-experimental[langfuse]` datasets.

## Setup

```bash
conda activate kedro-agentic-reflection-env   # or any Python >=3.10 venv
pip install -r requirements.txt

# Fill in credentials (the file is gitignored)
cp conf/local/credentials.template.yml conf/local/credentials.yml
# edit conf/local/credentials.yml — openai + langfuse_credentials
```

## Run

```bash
# Kedro pipelines (each individually, once nodes are added):
kedro run -p agent_run --params run_id=run_1
kedro run -p evaluation --params run_id=run_1
kedro run -p reflection --params reflection_id=refl_1,run_id=run_1
kedro run -p apply --params reflection_id=refl_1

# Streamlit dashboard:
streamlit run app/main.py

# Kedro-Viz:
kedro viz
```
