# Reflection Hub

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

**Enterprise self-improving AI agents, orchestrated with Kedro.** One platform investment, three business units impacted and governance built in.


![Reflection Hub](docs/assets/images/reflection_hub.png)

---

One platform runs the same governed loop for three business units: generate, evaluate, scout, reflect, approve, apply. This repository is a proof-of-concept with a Streamlit front end and synthetic data.

**Why Kedro?** The five pipelines (`campaign`, `evaluation`, `scouts`, `reflection`, `apply`) are written once and parameterised by `agent_id`. Adding a new business unit is configuration — new seed data, prompts, and eval cases under `data/{agent_id}/` — not new pipeline code. Kedro enforces declared inputs/outputs, versioned artifacts, and a reproducible run graph, which is what makes the governed loop auditable and portable across agents.

| Document | Audience |
| --- | --- |
| [`docs/Architecture.md`](docs/Architecture.md) | Executive |
| [`DESIGN.md`](DESIGN.md) | Technical |
| [`docs/ui/`](docs/ui/) | Static HTML mocks |

---

## Quick start

- Requires [uv](https://docs.astral.sh/uv/).
- Requires Langfuse for tracing

  **Self-hosted Langfuse (Podman):**
  ```bash
  podman machine init && podman machine start
  git clone https://github.com/langfuse/langfuse.git && cd langfuse
  podman-compose up -d
  curl http://localhost:3000/api/public/health   # → {"status":"ok"}
  # Set host: http://localhost:3000 in credentials.yml
  ```

- Project setup and run

  ```bash
  make setup
  # This will do `make install` and `make seed N=20` creating 20 eval cases and targets for each agent
  # You can run `make install` and `make seed N=5` if you want to demo 5 cases (which the project already has)
  
  cp conf/local/credentials.yml.example conf/local/credentials.yml
  # Required: openai.api_key
  # Langfuse traces / prompt registry): langfuse_credentials

  # (recommended) pre-populate the UI so the live demo doesn't wait on LLM calls
  # defaults to b2b_sales; pass agent=<id> for another agent (b2b_sales, consumer_mktg, customer_care)
  make run-cycle

  make app
  # This will open the app at `http://localhost:8501/`
  ```


![Reflection Hub Gif](docs/assets/reflection_hub.gif)


---

**Reset demo data:**

```bash
make seed        # all 3 agents, 20 cases each
make seed N=5    # fewer cases per agent
```

---

## Usage

| Command | Description |
| --- | --- |
| `make app` | Streamlit UI (`app/main.py`) |
| `make viz` | Kedro-Viz pipeline graph |
| `make run-cycle` | Full headless cycle (default: `b2b_sales`) |
| `make run-cycle agent=b2b_sales` | Full headless cycle for a specific agent. **Valid agent IDs:** `b2b_sales`, `consumer_mktg`, `customer_care` |



**Manual pipeline runs** (`agent_id` is required):

```bash
uv run kedro run --pipelines campaign,evaluation,scouts \
  --params "agent_id=b2b_sales,run_id=run_1"
```

More commands and parameters: [`DESIGN.md`](DESIGN.md).


---

## Project layout (abbreviated)

```
kedro-reflection-agent/
├── app/                            # Streamlit UI
│   ├── main.py                     # entry point
│   ├── pages/                      # org_overview · campaign
│   ├── components/                 # reusable UI widgets
│   ├── data_loader.py
│   ├── runner.py                   # triggers Kedro pipelines from UI
│   └── state.py
├── conf/
│   ├── base/                       # catalog (per-pipeline) + parameters
│   └── local/credentials.yml       # API keys (gitignored)
├── data/
│   ├── shared/                     # 20 customers, 15 products (seed)
│   ├── b2b_sales/                  # per-agent seed, prompts, outputs
│   ├── consumer_mktg/
│   ├── customer_care/
│   └── demo_state.json
├── docs/
│   ├── Architecture.md
│   ├── assets/                     # gif + images
│   └── ui/                         # HTML prototypes
├── src/kedro_reflection_agent/
│   ├── pipelines/
│   │   ├── campaign/               # generate outreach
│   │   ├── evaluation/             # score against rubric
│   │   ├── scouts/                 # find improvement opportunities
│   │   ├── reflection/             # synthesise prompt edits
│   │   └── apply/                  # write new prompt version
│   ├── models/
│   │   ├── shared/                 # campaign · evaluation · reflection · scouts
│   │   ├── b2b_sales/
│   │   ├── consumer_mktg/
│   │   └── customer_care/
│   ├── datasets/                   # custom Kedro dataset types
│   ├── utils/
│   └── hooks.py
├── scripts/seed_demo.py
├── DESIGN.md
└── Makefile
```

---

## Agents (demo)

| Agent | Role |
| --- | --- |
| B2B Sales | Enterprise outreach emails |
| Consumer Marketing | Plan & device upgrade offers |
| Customer Care | Support reply suggestions |

**Demo scale:** 5 scenarios × 3 agents on synthetic data; the Kedro loop scales to larger batch sizes without structural change.
