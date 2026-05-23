# kedro-reflection-agent

A Kedro + Streamlit demo of an **agentic reflection / continuous learning** loop.

A B2B campaign agent (telco sales) generates personalised outreach emails.
After an evaluation pass, a meta-agent reflects on the failures and proposes
updates to the system prompt, the skill file, and the eval set itself.
Re-running the agent against the new artifacts produces visibly better emails.

For the full pipeline design and rationale see [`DESIGN.md`](DESIGN.md).

## Status

| Component                | Status                                                                     |
| ------------------------ | -------------------------------------------------------------------------- |
| Synthetic data + prompts | ✅ committed under `data/`                                                 |
| `campaign` pipeline      | ✅ implemented — generates emails + emits Langfuse traces                  |
| `evaluation` pipeline    | ✅ implemented — drives a Langfuse `run_experiment(...)`                   |
| `reflection` pipeline    | ✅ implemented — meta-agent proposes new prompt, skill, and eval cases     |
| `apply` pipeline         | ✅ implemented — commits approved proposal to live locations               |
| Streamlit dashboard      | ✅ implemented — 3-step interactive demo with Langfuse observability panel |

End-to-end demo is **fully runnable**: campaign → evaluation → reflection → apply → campaign → evaluation, all orchestrated through the UI or CLI.

## Project shape

```
kedro-reflection-agent/
├── conf/
│   ├── base/
│   │   ├── catalog.yml                 # pipeline-agnostic (default_dataset)
│   │   ├── catalog_campaign.yml
│   │   ├── catalog_evaluation.yml
│   │   ├── catalog_reflection.yml
│   │   ├── catalog_apply.yml
│   │   └── parameters.yml              # runtime defaults
│   ├── local/
│   │   ├── credentials.yml             # gitignored — real keys go here
│   │   └── credentials.yml.example    # template (committed)
│   └── logging.yml
├── data/
│   ├── seed/                           # synthetic customers + products
│   ├── campaign/                       # targets, system prompt, skill file
│   ├── evaluation/                     # eval cases + judge prompt
│   ├── reflection/                     # meta-agent prompt
│   ├── demo_state.json                 # UI state machine (written by seed script)
│   └── outputs/                        # all pipeline writes go here (gitignored)
│       ├── runs/{run_id}/
│       └── reflections/{reflection_id}/
├── src/kedro_reflection_agent/
│   ├── data_models.py                  # shared Pydantic models
│   ├── pipeline_registry.py
│   ├── settings.py
│   └── pipelines/
│       ├── _common.py                  # build_structured_chain, utc_now_iso
│       ├── campaign/{nodes.py, pipeline.py}
│       ├── evaluation/{nodes.py, pipeline.py}
│       ├── reflection/{nodes.py, pipeline.py}
│       └── apply/{nodes.py, pipeline.py}
├── app/                                # Streamlit dashboard
│   ├── main.py                         # entry point + reset logic
│   ├── runner.py                       # blocking kedro subprocess runner
│   ├── state.py                        # DemoState machine + persistence
│   ├── ui_components.py                # shared UI chrome
│   ├── charts.py                       # Plotly chart helpers
│   ├── embeds.py                       # Langfuse + Kedro-Viz panel renderers
│   ├── langfuse_analytics.py           # Langfuse public API client
│   ├── kedro_viz_server.py             # background Kedro-Viz subprocess
│   └── components/
│       ├── step_1_run.py               # Step 1: generate + evaluate
│       ├── step_2_reflect.py           # Step 2: reflect + apply
│       └── step_3_rerun.py             # Step 3: re-run + compare
├── scripts/
│   └── seed_demo.py                    # restore v1 baseline; wipe run outputs
├── tests/
├── Makefile
└── DESIGN.md
```

## Synthetic data

All input data is hand-crafted and committed. There is no data-generation step.

| File                                             | Items | Schema                                                                                                         |
| ------------------------------------------------ | ----- | -------------------------------------------------------------------------------------------------------------- |
| `data/seed/customers.json`                       |  10   | `customer_id`, `company_name`, `industry`, `company_size`, `employee_count`, `current_products`, `account_tenure_years`, `primary_contact_name`, `primary_contact_role`, `region` |
| `data/seed/products.json`                        |   5   | `product_id`, `name`, `short_description`, `target_segment`, `key_benefits`, `pricing_tier`                    |
| `data/campaign/targets.json`                     |  20   | `case_id`, `customer_id`, `product_id`                                                                         |
| `data/campaign/prompts/system_prompt.json`       |   1   | chat-style Langfuse prompt; v1 is deliberately mediocre                                                        |
| `data/campaign/skills/b2b_email_style.md`        |   1   | markdown skill file injected into the system prompt via `{skill}`                                              |
| `data/evaluation/eval_cases.json`                |  20   | Langfuse dataset items with rubric (`required_mentions`, `forbidden_mentions`, `expected_cta`, `expected_tone`) |
| `data/evaluation/prompts/judge_prompt.json`      |   1   | chat-style Langfuse prompt for the LLM judge                                                                   |
| `data/reflection/prompts/meta_agent_prompt.json` |   1   | chat-style prompt for the reflection meta-agent                                                                |

`case_id` is shared between `targets.json` and `eval_cases.json` so evaluation can join emails to rubrics by id.

## What's built

### `campaign` pipeline — 3 nodes

```
agent_context_node          ->  agent_context
prepare_agent_inputs_node   ->  agent_inputs
generate_emails_node        ->  emails        (data/outputs/runs/{run_id}/emails/{case_id}.json)
                                run_metadata  (data/outputs/runs/{run_id}/run_metadata.json)
```

Composes a `ChatPromptTemplate | LLM.with_structured_output(EmailOutput)` chain per case, attaching a Langfuse callback so every generation produces a trace.

### `evaluation` pipeline — 5 nodes

```
judge_context_node              ->  judge_context
init_heuristic_evaluators_node  ->  4 heuristic evaluator callables
init_judge_evaluator_node       ->  1 combined LLM-judge evaluator (3 Evaluations per call)
make_campaign_task_node         ->  task callable (disk lookup by case_id)
run_experiment_node             ->  per_case_scores   (data/outputs/runs/{run_id}/per_case_scores.json)
                                    aggregate_scores  (data/outputs/runs/{run_id}/aggregate_scores.json)
                                    + named dataset run in Langfuse
```

Seven scorers: four deterministic heuristics (`subject_present`, `length_in_range`, `no_fake_skus`, `cta_present`) and three LLM-judge dimensions (`writing_quality`, `personalization`, `groundedness`). One judge LLM call per email (not per dimension).

### `reflection` pipeline — 3 nodes

```
meta_agent_context_node         ->  meta_agent_context
prepare_reflection_context_node ->  reflection_context
reflect_node                    ->  summary.md             (data/outputs/reflections/{reflection_id}/)
                                    proposed_prompt.json
                                    proposed_skill.md
                                    proposed_eval_cases.json
```

The meta-agent reads the current prompt + skill + worst-N failing cases and produces a structured proposal. Errored experiment cases (no local email) are filtered out. Reflection is open-loop — it never touches live artifacts.

### `apply` pipeline — 1 node

```
commit_reflection_node  ->  system_prompt  (new version pushed to Langfuse)
                            skill_text     (data/campaign/skills/b2b_email_style.md overwritten)
                            eval_cases     (new items pushed to Langfuse dataset)
                            apply_history  (data/outputs/apply_history.json appended)
```

Takes an approved `reflection_id` and commits all three artifacts, recording an audit row.

## Quick start

This project uses [uv](https://docs.astral.sh/uv/) for environment management.

```bash
brew install uv            # macOS; or: curl -LsSf https://astral.sh/uv/install.sh | sh
make setup                 # uv sync --extra dev + restore seed data
cp conf/local/credentials.yml.example conf/local/credentials.yml
# Edit credentials.yml — fill in openai.api_key + langfuse_credentials
```

You'll need a Langfuse project with:
- prompt `b2b-email-system-prompt`
- prompt `b2b-email-judge-prompt`
- dataset `b2b-campaign-agent-eval`

Add `project_id` to `langfuse_credentials` to enable deep-links in the observability panel.

### Self-hosting Langfuse v3 (Podman)

```bash
podman machine init && podman machine start   # macOS only
git clone https://github.com/langfuse/langfuse.git && cd langfuse
podman-compose up -d
curl http://localhost:3000/api/public/health  # → {"status":"ok"}
```

Set `host: http://localhost:3000` in `conf/local/credentials.yml`. No API rate limits on a self-hosted instance.

## Makefile shortcuts

| Command          | What it does                                                     |
| ---------------- | ---------------------------------------------------------------- |
| `make install`   | `uv sync --extra dev` — create `.venv` and install all deps      |
| `make setup`     | `install` + `seed` — full first-time setup                       |
| `make seed`      | Restore v1 baseline; wipe run outputs (all 20 cases)             |
| `make seed N=3`  | Seed only the first N eval cases and campaign targets            |
| `make reset`     | Alias for `seed`                                                 |
| `make app`       | `uv run streamlit run app/main.py`                               |
| `make viz`       | `uv run kedro viz run`                                           |
| `make test`      | `uv run python -m pytest -q`                                     |
| `make run-cycle` | Full six-step pipeline cycle headless (no UI)                    |

> `data/outputs/apply_history.json` is preserved across resets so you can track apply cycles across sessions.

## Run

```bash
make app    # launch the interactive UI

# Or run each step manually:
uv run kedro run --pipelines campaign    --params "run_id=run_1"
uv run kedro run --pipelines evaluation  --params "run_id=run_1"
uv run kedro run --pipelines reflection  --params "run_id=run_1,reflection_id=refl_1"
uv run kedro run --pipelines apply       --params "reflection_id=refl_1"
uv run kedro run --pipelines campaign    --params "run_id=run_2"
uv run kedro run --pipelines evaluation  --params "run_id=run_2"
```

## Configuration

| Param                      | Default       | Used by                                |
| -------------------------- | ------------- | -------------------------------------- |
| `run_id`                   | `default`     | output paths for campaign + evaluation |
| `model_name`               | `gpt-4o-mini` | campaign LLM                           |
| `system_prompt_version`    | `1`           | which Langfuse system-prompt version   |
| `judge_model_name`         | `gpt-4o`      | evaluation LLM                         |
| `judge_prompt_version`     | `1`           | which Langfuse judge-prompt version    |
| `passing_threshold`        | `0.92`        | per-case mean cutoff for `n_passing`   |
| `body_length_min` / `_max` | `300` / `2000`| heuristic body-length scorer           |
| `reflection_id`            | `refl_1`      | output paths for reflection + apply    |

## Outputs

```
data/outputs/
├── runs/{run_id}/
│   ├── emails/{case_id}.json     # one file per generated email
│   ├── run_metadata.json         # model, versions, counts, timestamps
│   ├── per_case_scores.json      # case_id, evaluations, mean_score, passing
│   └── aggregate_scores.json     # mean per scorer, pass_rate, dataset_run_url
├── reflections/{reflection_id}/
│   ├── summary.md                # narrative: identified / fixed / reasons
│   ├── proposed_prompt.json      # new system prompt messages
│   ├── proposed_skill.md         # new skill file content
│   └── proposed_eval_cases.json  # new eval cases derived from failures
└── apply_history.json            # append-only audit log
```

## Langfuse observability

Every Langfuse tab shows (when `langfuse_credentials` is configured):

- **Metrics row** — total traces, LLM cost today, observations today
- **Score averages** bar chart — all 7 eval dimensions averaged across runs
- **Token usage by model** — stacked input/output tokens with total cost (from `/api/public/metrics`)
- **Daily traces** and **daily cost** time-series (from `/api/public/metrics/daily`)
- **Recent traces** expander with deep-links into the Langfuse UI

## Known shortcuts (intentional)

- **Skill file on disk only.** The system prompt and judge prompt are Langfuse-versioned; the skill markdown is a plain `text.TextDataset`. A future slice can version it in Langfuse too.
- **`evaluation` reuses cached emails.** The experiment task is a disk lookup — not a re-invocation — so the UI email and the scored email are byte-identical.
- **Scores mirrored to disk.** `per_case_scores.json` and `aggregate_scores.json` let `reflection` work offline without a Langfuse round-trip.

## Where to look next

- [`DESIGN.md`](DESIGN.md) — full per-pipeline contract for all four pipelines
- `src/kedro_reflection_agent/data_models.py` — Pydantic models shared by all pipelines
- `src/kedro_reflection_agent/pipelines/_common.py` — shared helpers
