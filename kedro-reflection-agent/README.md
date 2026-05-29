# Reflection Hub

> **Self-improving agent platform for telco.**
> One platform investment, N business units. Governance built in. Value compounds as the portfolio grows.

Three AI agents run the same five-pipeline loop — generate → evaluate → scout → reflect → apply. A shared Portfolio Intelligence layer surfaces quality trends, issue patterns, and cross-agent learnings. Every change goes through a human approval gate before it touches production.

For the full system design see [`docs/enterprise-architecture.md`](docs/enterprise-architecture.md).

---

## Why this architecture

**Scale** — One platform investment serves N business units. Evaluation, governance, and audit are not rebuilt per team. Adding a fourth agent is a configuration exercise: new data files under `data/{agent_id}/`, new Langfuse prompts and dataset. Zero code changes.

**Governance built in** — No change touches production without a human approval gate. Every prompt version, every skill update, every apply event is traceable to a run ID.

**Compounding value** — A failure caught in one unit becomes a regression test there *and* surfaces an opportunity for the others. The platform gets smarter as the portfolio grows.

---

## System layers

```
╔══════════════════════════════════════════════════════════════════════╗
║                  PORTFOLIO INTELLIGENCE LAYER                        ║
║  Quality Trend · Issue Matrix · Cross-Agent Learning · Audit Roll-up ║
╚══════════════╤═════════════════╤════════════════════╤═══════════════╝
               │                 │                    │
    ┌──────────▼──────┐  ┌───────▼──────────┐  ┌─────▼───────────────┐
    │  B2B Sales       │  │ Consumer Mktg    │  │  Customer Care       │
    │  Enterprise      │  │  Plan & device   │  │   Support reply      │
    │  outreach emails │  │  upgrade offers  │  │   suggestions        │
    │                  │  │                  │  │                      │
    │  Generate        │  │  Generate        │  │  Generate            │
    │  Evaluate        │  │  Evaluate        │  │  Evaluate            │
    │  Scout → signals │  │  Scout → signals │  │  Scout → signals     │
    │  Reflect         │  │  Reflect         │  │  Reflect             │
    │  ✋ Approve       │  │  ✋ Approve       │  │  ✋ Approve           │
    │  Apply           │  │  Apply           │  │  Apply               │
    └──────────────────┘  └──────────────────┘  └──────────────────────┘
               │                 │                    │
╔══════════════▼═════════════════▼════════════════════▼═══════════════╗
║                    SHARED PLATFORM SERVICES                          ║
║  Prompt Registry · Skill Library · Eval Framework · Audit Log        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Portfolio Intelligence

| View | Question answered | UI page | Audience |
|---|---|---|---|
| **Quality Trend** | Who's improving, stalling, regressing? | Org Overview | Leadership |
| **Issue Matrix** | Which failure modes are unit-specific vs. systemic? | Org Overview | Platform team |
| **Cross-Agent Learning** | When a fix in one unit matches an open failure in another, should it travel? | Org Overview | Platform team |
| **Audit Roll-up** | What changed, when, who approved it, any rollbacks? | Campaigns | Governance |

---

## Status

| Component | Status |
|---|---|
| `campaign` pipeline | ✅ — generates outputs + Langfuse traces |
| `evaluation` pipeline | ✅ — LLM judge + heuristics, per-agent scorer dimensions |
| `scouts` pipeline | ✅ — 5 pattern scouts, signal index |
| `reflection` pipeline | ✅ — meta-agent proposes prompt / skill / eval cases |
| `apply` pipeline | ✅ — commits approved proposal, audit log |
| `RunIndexHook` | ✅ — cross-run audit index after each pipeline |
| B2B Sales agent | ✅ end-to-end |
| Consumer Marketing agent | ⬜ data + models ready; Langfuse setup pending |
| Customer Care agent | ⬜ data + models ready; Langfuse setup pending |
| Streamlit UI | ✅ — 3-step demo (B2B) |
| Portfolio Intelligence UI | ⬜ HTML prototypes in `docs/ui/` — not wired to live data yet |

---

## Agent loop — invariant shape

Every agent follows the same seven-step loop. The pipeline code does not change when adding an agent.

| Step | What happens | UI touchpoint |
|---|---|---|
| **Generate** | Agent drafts outputs against live targets | Campaigns — Stage 1 |
| **Evaluate** | LLM judge + heuristics score each output against domain rubric | Campaigns — Stage 1 Langfuse tab |
| **Scout** | Rule-based detectors scan outputs and emit signals | Campaigns — Stage 2 Signals tab |
| **Reflect** | Meta-agent reads signal clusters and worst-case outputs | Campaigns — Stage 3 |
| **Propose** | Improved prompt, skill file, regression cases written to disk | Campaigns — Stage 3 Proposal tab |
| **Human Approval** | Reviewer inspects the diff before anything goes live | Campaigns — Stage 4 gate |
| **Apply** | Approved changes versioned into Langfuse; audit row appended | Campaigns — Stage 4 Run Logs |

---

## Agents

| Agent | Description | Judge dimensions |
|---|---|---|
| `b2b_sales` | Enterprise outreach emails | writing_quality, personalization, groundedness |
| `consumer_mktg` | Plan & device upgrade offers | offer_relevance, personalisation, urgency_cta, tone, compliance |
| `customer_care` | Empathetic support replies | empathy_opener, resolution_clarity, tone, compliance, escalation_avoidance |

All agents share four heuristic scorers: `subject_present`, `length_in_range`, `no_fake_skus`, `cta_present`.

---

## Pattern scouts

Five deterministic, LLM-free detectors between Evaluate and Reflect.

| Scout | Triggers when… | Confidence |
|---|---|---|
| `rubric_miss` | Any rubric field not met on ≥ 2 cases | `high` |
| `score_regression` | Any dimension drops > 10 pts vs. rolling 5-run average | `medium` / `high` if > 20 pts |
| `hallucination_flag` | Forbidden mention or fabricated detail detected on ≥ 1 case | `high` |
| `tone_drift` | Tone dimension below floor for ≥ 3 consecutive cases | `medium` |
| `cross_unit_pattern` | Same `signal_type` in ≥ 2 agents in the same rolling window | `high` |

Design rules: pure and deterministic (no LLM calls), O(n) over outputs, `reason` field is self-contained (quotes threshold + observed value).

---

## Evaluation framework

Two distinct layers — often conflated:

**1. Shared infrastructure** (identical across all agents)
- `run_experiment()` Langfuse experiment runner
- Kedro pipeline shape and catalog pattern
- 4-slot heuristic scorer scaffold
- `CaseScore` / `AggregateScore` disk schema

**2. Per-agent configuration** (swapped via `agent_id` at runtime)
- `judge_prompt` — scoring criteria and dimension definitions
- `JudgeScore` model — scorer names derived from model fields
- Heuristic implementations — domain-specific structural checks
- Eval dataset — separate Langfuse dataset per agent

**3. Per-case rubric** (on every eval case)
```json
{
  "required_mentions": ["fleet management", "uptime SLA"],
  "forbidden_mentions": ["generic connectivity"],
  "expected_cta": "demo",
  "expected_tone": "consultative"
}
```

---

## Storage & data layer

| Store | Path | Written by | Read by |
|---|---|---|---|
| **Run outputs** | `data/{agent_id}/outputs/runs/{run_id}/` | campaign, evaluation, scouts | reflection, Portfolio Intelligence |
| **Signal store** | `…/signals.json` | scouts | reflection (threshold check), Portfolio Intelligence |
| **Run index** | `data/outputs/run_index.json` | `RunIndexHook` (after each pipeline) | Portfolio Intelligence, UI |
| **Signal index** | `data/outputs/signal_index.json` | `cross_unit_pattern` scout | `cross_unit_pattern` scout, Portfolio Intelligence |
| **Reflection store** | `data/{agent_id}/outputs/reflections/{reflection_id}/` | reflection, apply | human reviewer, apply pipeline |
| **Apply history** | `data/outputs/apply_history.json` | apply pipeline (append-only) | Portfolio Intelligence, governance |
| **Prompt registry** | Langfuse (versioned) | apply pipeline | campaign (injected at runtime) |
| **Skill library** | `data/{agent_id}/campaign/skills/` | apply pipeline | campaign (injected at runtime) |

> POC approach: all stores are flat JSON files. Natural migration path: signal store + run index → SQLite or DuckDB; prompts + eval datasets stay in Langfuse.

---

## Project shape

```
kedro-reflection-agent/
├── conf/base/
│   ├── catalog.yml                     # {default_dataset} override only
│   ├── catalog_campaign.yml
│   ├── catalog_evaluation.yml
│   ├── catalog_scouts.yml
│   ├── catalog_reflection.yml
│   ├── catalog_apply.yml
│   └── parameters.yml                  # agent_id is mandatory (no default)
├── data/
│   ├── shared/seed/
│   │   ├── customers.json              # 20 global customer base records
│   │   └── products.json               # 15 global product base records
│   └── {agent_id}/
│       ├── seed/
│       │   ├── customer_profiles.json  # agent-specific enrichment (FK: customer_id)
│       │   ├── product_details.json    # agent-specific enrichment (FK: product_id)
│       │   └── targets.json            # (case_id, customer_id, product_id)
│       ├── campaign/prompts/ + skills/
│       ├── evaluation/eval_cases.json + prompts/
│       ├── reflection/prompts/
│       └── outputs/                    # gitignored
├── src/kedro_reflection_agent/
│   ├── models/
│   │   ├── shared/                     # EmailOutput, CaseScore, Signal, RunIndexEntry, …
│   │   ├── b2b_sales/                  # JudgeScore, CustomerProfile, ProductDetails
│   │   ├── consumer_mktg/              # JudgeScore, CustomerProfile, ProductDetails
│   │   └── customer_care/              # JudgeScore, CustomerProfile, ProductDetails
│   ├── hooks.py                        # RunIndexHook
│   ├── settings.py
│   └── pipelines/
│       ├── campaign/ evaluation/ scouts/ reflection/ apply/
│       └── _common.py
├── app/                                # Streamlit dashboard
├── docs/
│   ├── enterprise-architecture.md
│   └── ui/
│       ├── index.html                  # Org Overview prototype
│       └── campaign.html               # Campaigns page prototype
├── scripts/seed_demo.py
└── Makefile
```

---

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
brew install uv
make setup
cp conf/local/credentials.yml.example conf/local/credentials.yml
# fill in: openai.api_key, langfuse_credentials (host, public_key, secret_key, project_id)
```

**Langfuse setup** — one dataset and two prompts per agent. For B2B:
```
Dataset:  b2b_sales-eval
Prompt:   b2b_sales-system-prompt   ← seed from data/b2b_sales/campaign/prompts/system_prompt.json
Prompt:   b2b_sales-judge-prompt    ← seed from data/b2b_sales/evaluation/prompts/judge_prompt.json
```

**Self-hosted Langfuse (Podman):**
```bash
podman machine init && podman machine start
git clone https://github.com/langfuse/langfuse.git && cd langfuse
podman-compose up -d
curl http://localhost:3000/api/public/health   # → {"status":"ok"}
# Set host: http://localhost:3000 in credentials.yml
```

**UI prototypes (no backend required):**
```bash
python -m http.server 8080 --directory docs/ui
# open http://localhost:8080/index.html      — Org Overview
# open http://localhost:8080/campaign.html   — Campaigns page
```

---

## Makefile shortcuts

| Command | What it does |
|---|---|
| `make install` | `uv sync --extra dev` — create `.venv` and install all deps |
| `make setup` | `install` + `seed` — full first-time setup |
| `make seed` | Reset all 3 agents to v1 baseline; wipe run outputs |
| `make seed N=5` | Seed only first 5 cases per agent |
| `make seed AGENT=b2b_sales` | Reset one agent only |
| `make seed AGENT=b2b_sales N=3` | One agent, 3 cases |
| `make reset` | Alias for `seed` |
| `make app` | Launch Streamlit UI (`streamlit run app/main.py`) |
| `make viz` | Launch Kedro-Viz pipeline graph |
| `make test` | Run pytest |
| `make run-cycle` | Full headless demo cycle for b2b_sales |

> `data/outputs/apply_history.json` is preserved across resets.

---

## Running pipelines manually

`agent_id` is mandatory — there is no default fallback.

```bash
# Full default loop (campaign + evaluation + scouts)
kedro run --params "agent_id=b2b_sales,run_id=run_1"

# Individual pipelines
kedro run --pipeline campaign    --params "agent_id=b2b_sales,run_id=run_1"
kedro run --pipeline evaluation  --params "agent_id=b2b_sales,run_id=run_1"
kedro run --pipeline scouts      --params "agent_id=b2b_sales,run_id=run_1"
kedro run --pipeline reflection  --params "agent_id=b2b_sales,run_id=run_1,reflection_id=refl_1"
kedro run --pipeline apply       --params "agent_id=b2b_sales,reflection_id=refl_1"

# Other agents
kedro run --params "agent_id=consumer_mktg,run_id=run_1"
kedro run --params "agent_id=customer_care,run_id=run_1"
```

---

## Parameters

| Param | Default | Notes |
|---|---|---|
| `agent_id` | **mandatory** | no fallback — must be passed explicitly |
| `run_id` | `default` | controls output path |
| `reflection_id` | `refl_1` | controls reflection output path |
| `model_name` | `gpt-4o-mini` | campaign LLM |
| `system_prompt_version` | `1` | Langfuse prompt version |
| `judge_model_name` | `gpt-4o` | evaluation LLM judge |
| `judge_prompt_version` | `1` | Langfuse judge prompt version |
| `passing_threshold` | `0.92` | per-case mean cutoff for `n_passing` |
| `body_length_min/max` | `300/2000` | heuristic length scorer bounds |
| `meta_agent_model_name` | `gpt-4o` | reflection meta-agent |

Scout thresholds (all in `parameters.yml`): `scout_regression_delta_medium/high`, `scout_regression_window`, `scout_rubric_miss_min_cases`, `scout_hallucination_min_cases`, `scout_tone_floor/min_cases`, `scout_cross_unit_min_agents/window`.

---

## Output layout

```
data/{agent_id}/outputs/
├── runs/{run_id}/
│   ├── emails/{case_id}.json     # generated output per case
│   ├── run_metadata.json         # model, versions, counts, timestamps
│   ├── per_case_scores.json      # per-case evaluations, mean_score, passing
│   ├── aggregate_scores.json     # pass_rate, mean_per_scorer, Langfuse URL
│   └── signals.json              # scout signals for this run
└── reflections/{reflection_id}/
    ├── summary.md
    ├── proposed_prompt.json
    ├── proposed_skill.md
    └── proposed_eval_cases.json

data/outputs/                     # cross-agent shared stores
├── run_index.json                # rolling audit index — all agents, all runs
├── signal_index.json             # rolling cross-agent signal log
└── apply_history.json            # append-only apply audit log
```

---

## Where to look next

| File | What's there |
|---|---|
| [`docs/enterprise-architecture.md`](docs/enterprise-architecture.md) | Full system design, mermaid flowchart, storage layer |
| `src/kedro_reflection_agent/models/` | All Pydantic models — shared and per-agent |
| `src/kedro_reflection_agent/hooks.py` | `RunIndexHook` — cross-run audit index |
| `src/kedro_reflection_agent/pipelines/_common.py` | Shared helpers |
| `conf/local/credentials.yml.example` | Credentials template |
| `docs/ui/index.html` | Org Overview UI prototype |
| `docs/ui/campaign.html` | Campaigns page UI prototype |
