# kedro-reflection-agent

A Kedro + Streamlit demo of an **agentic reflection / continuous learning** loop.

A B2B campaign agent (telco sales) generates personalised outreach emails.
After an evaluation pass, a meta-agent reflects on the failures and proposes
updates to the system prompt, the skill file, and the eval set itself.
Re-running the agent against the new artifacts produces visibly better emails.

For the full pipeline design and rationale see [`DESIGN.md`](DESIGN.md).

## Status

| Component                | Status                                                        |
| ------------------------ | ------------------------------------------------------------- |
| Synthetic data + prompts | committed under `data/` (see [Synthetic data](#synthetic-data)) |
| `campaign` pipeline      | implemented — generates emails + emits Langfuse traces        |
| `evaluation` pipeline    | implemented — drives a Langfuse `run_experiment(...)`         |
| `reflection` pipeline    | skeleton (empty `pipeline.py`, catalog stub)                  |
| `apply` pipeline         | skeleton (empty `pipeline.py`, catalog stub)                  |
| Streamlit dashboard      | scaffold only (`app/main.py`, per-step components)            |

End-to-end demo is **half-built**: you can already run `campaign` → `evaluation`
for any `run_id` and see scores both on disk and in Langfuse.

## Project shape

```
kedro-reflection-agent/
├── conf/
│   ├── base/
│   │   ├── catalog.yml                 # pipeline-agnostic (default_dataset)
│   │   ├── catalog_campaign.yml        # one catalog file per pipeline
│   │   ├── catalog_evaluation.yml
│   │   ├── catalog_reflection.yml      # stub
│   │   ├── catalog_apply.yml           # stub
│   │   └── parameters.yml              # runtime defaults
│   ├── local/credentials.yml.example   # template; real one is gitignored
│   └── logging.yml                     # silences known-noisy WARNINGs
├── data/
│   ├── seed/                           # synthetic customers + products
│   ├── campaign/                       # targets, system prompt, skill file
│   ├── evaluation/                     # eval cases + judge prompt
│   ├── reflection/                     # (meta-agent prompt — placeholder)
│   └── outputs/                        # all pipeline writes go here
│       ├── runs/{run_id}/              # campaign + evaluation outputs
│       └── reflections/{reflection_id}/  # future
├── src/kedro_reflection_agent/
│   ├── data_models.py                  # shared Pydantic models
│   ├── pipelines/
│   │   ├── _common.py                  # build_structured_chain, utc_now_iso
│   │   ├── campaign/{nodes.py, pipeline.py}
│   │   ├── evaluation/{nodes.py, pipeline.py}
│   │   ├── reflection/{nodes.py, pipeline.py}  # empty
│   │   └── apply/{nodes.py, pipeline.py}       # empty
│   └── settings.py                     # warning filters
├── app/                                # Streamlit dashboard scaffold
│   ├── main.py, runner.py, state.py
│   └── components/                     # one file per demo step
├── tests/
└── DESIGN.md                           # source of truth for the plan
```

Both halves share one venv. Streamlit (once wired up) will invoke Kedro via
subprocess (`kedro run -p <pipeline>`) and read back from `data/outputs/`.
Prompts, eval cases, and traces live partly on disk and partly in Langfuse,
backed by the experimental `kedro_datasets_experimental.langfuse` datasets
(installed via the `langfuse` extra on `kedro-datasets`).

## Synthetic data

All input data is hand-crafted and committed. There's no data-generation step.

| File                                         | Items | Schema                                                                                                                       |
| -------------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------- |
| `data/seed/customers.json`                   |  10   | `customer_id`, `company_name`, `industry`, `company_size`, `employee_count`, `current_products`, `account_tenure_years`, `primary_contact_name`, `primary_contact_role`, `region` |
| `data/seed/products.json`                    |   5   | `product_id`, `name`, `short_description`, `target_segment`, `key_benefits`, `pricing_tier`                                  |
| `data/campaign/targets.json`                 |  20   | `case_id`, `customer_id`, `product_id` — the (customer × product) pairs the agent generates emails for                       |
| `data/campaign/prompts/system_prompt.json`   |   1   | chat-style Langfuse prompt; v0 is deliberately mediocre so reflection has room to improve it                                 |
| `data/campaign/skills/b2b_email_style.md`    |   1   | markdown skill file injected into the system prompt via `{skill}`                                                            |
| `data/evaluation/eval_cases.json`            |  20   | Langfuse dataset items: `id`, `input` (`customer_id` + `product_id`), `expected_output.rubric` (`required_mentions`, `forbidden_mentions`, `expected_cta`, `expected_tone`, `notes`) |
| `data/evaluation/prompts/judge_prompt.json`  |   1   | chat-style Langfuse prompt for the LLM judge                                                                                 |

Conventions:

- `case_id` is shared between `data/campaign/targets.json` and
  `data/evaluation/eval_cases.json[].id`. This lets `evaluation` join the
  campaign-generated email (by case_id) against the case's rubric.
- The 20 cases deliberately span industries, company sizes, and upsell vs
  cross-sell scenarios so the v0 baseline produces a mix of passes and
  near-misses — that mix is what `reflection` will eventually consume.

## What's built

### `campaign` pipeline — 3 nodes

```
agent_context_node          ->  agent_context (LLMContext)
prepare_agent_inputs_node   ->  agent_inputs  (list of {case_id, customer, product})
generate_emails_node        ->  emails        (data/outputs/runs/{run_id}/emails/{case_id}.json)
                                run_metadata  (data/outputs/runs/{run_id}/run_metadata.json)
```

For each campaign target it composes a `ChatPromptTemplate | LLM.with_structured_output(EmailOutput)` chain and runs it once per case, attaching a Langfuse callback so every generation produces a trace.

### `evaluation` pipeline — 5 nodes

```
judge_context_node              ->  judge_context  (LLMContext)
init_heuristic_evaluators_node  ->  4 heuristic evaluator callables
init_judge_evaluator_node       ->  1 combined LLM-judge evaluator (returns 3 Evaluations)
make_campaign_task_node         ->  task callable (looks up emails by case_id)
run_experiment_node             ->  per_case_scores   (data/outputs/runs/{run_id}/per_case_scores.json)
                                    aggregate_scores  (data/outputs/runs/{run_id}/aggregate_scores.json)
                                    + a named dataset run in Langfuse
```

Drives a Langfuse `DatasetClient.run_experiment(...)`. The experiment task is an in-memory lookup of the campaign-generated email — no LLM call inside the task — so what's scored is byte-identical to what was generated. Each evaluation run is stored in Langfuse as `campaign_{run_id}_prompt_v{N}`, so successive runs (before vs after reflection) are trivially comparable in the UI.

Seven scorers in total: four deterministic heuristics (`subject_present`, `length_in_range`, `no_fake_skus`, `cta_present`) and three LLM-judge dimensions returned by one combined call (`writing_quality`, `personalization`, `groundedness`).

## Quick start

```bash
make setup          # create .venv, install deps, restore seed data
```

Then fill in credentials (the real file is gitignored):

```bash
cp conf/local/credentials.yml.example conf/local/credentials.yml
# Edit conf/local/credentials.yml — openai.api_key + langfuse_credentials
```

You'll need a Langfuse project with two prompts and one dataset created (the
catalog references them by name):

- prompt `b2b-email-system-prompt` (matches `data/campaign/prompts/system_prompt.json`)
- prompt `b2b-email-judge-prompt`  (matches `data/evaluation/prompts/judge_prompt.json`)
- dataset `b2b-campaign-agent-eval` (synced from `data/evaluation/eval_cases.json`)

With `sync_policy: local` (the default in this project), the experimental
Langfuse datasets read from local disk and push to Langfuse on save, so a
first-time setup can be done by running each pipeline once.

## Makefile shortcuts

| Command | What it does |
|---|---|
| `make install` | Create `.venv` and install all dependencies |
| `make setup` | `install` + `seed` — full first-time setup |
| `make seed` | Restore v1 prompt, skill file & eval cases; wipe run outputs |
| `make reset` | Alias for `seed` — use after a demo to start clean |
| `make app` | Launch the Streamlit dashboard (`streamlit run app/main.py`) |
| `make viz` | Start Kedro-Viz standalone |
| `make test` | Run the test suite |
| `make run-cycle` | Full three-step pipeline cycle without the UI |

> **Reset vs seed:** both do the same thing — restore the weak v1 baseline and
> clear `data/outputs/runs/` and `data/outputs/reflections/`. The
> `data/outputs/apply_history.json` log is intentionally preserved so you can
> track how many times the loop has been applied across sessions.

## Run

```bash
# Launch the interactive demo UI:
make app

# Or run each pipeline step manually:
kedro run --pipelines campaign    --params "run_id=run_1"
kedro run --pipelines evaluation  --params "run_id=run_1"
kedro run --pipelines reflection  --params "run_id=run_1,reflection_id=refl_1"
kedro run --pipelines apply       --params "reflection_id=refl_1"
kedro run --pipelines campaign    --params "run_id=run_2"
kedro run --pipelines evaluation  --params "run_id=run_2"

# Visualise the pipeline topology:
make viz
```

## Configuration

Runtime defaults live in `conf/base/parameters.yml`. Override any of them on
the CLI with `--params key=value,key2=value2`.

| Param                     | Default          | Used by                                |
| ------------------------- | ---------------- | -------------------------------------- |
| `run_id`                  | `default`        | output paths for campaign + evaluation |
| `model_name`              | `gpt-4o-mini`    | campaign LLM                           |
| `system_prompt_version`   | `1`              | which Langfuse system-prompt version   |
| `judge_model_name`        | `gpt-4o`         | evaluation LLM (deliberately bigger)   |
| `judge_prompt_version`    | `1`              | which Langfuse judge-prompt version    |
| `passing_threshold`       | `0.92`           | per-case mean cutoff for `n_passing`   |
| `body_length_min` / `_max`| `300` / `2000`   | heuristic body-length scorer           |

Catalogs are split per pipeline (`conf/base/catalog_<pipeline>.yml`). One
project-wide entry — the `{default_dataset}` pattern that backs in-memory node
outputs as `MemoryDataset(copy_mode="assign")` — lives in
`conf/base/catalog.yml`.

## Outputs

Pipelines only ever write under `data/outputs/`:

```
data/outputs/
└── runs/
    └── {run_id}/
        ├── emails/{case_id}.json     # one file per generated email
        ├── run_metadata.json         # model, versions, counts, timestamps
        ├── per_case_scores.json      # case_id, evaluations, mean_score, passing
        └── aggregate_scores.json     # mean per scorer, pass_rate, dataset_run_url
```

Everything else under `data/` (seed, prompts, skills, eval cases) is input and
committed to git. Only `data/outputs/` is gitignored.

## Known shortcuts (intentional, revisit later)

These are deliberate simplifications taken to keep the first slice small.
None of them block the reflection loop; each can be replaced without changing
the pipeline topology.

- **Skill file lives on disk only.** The system prompt and judge prompt are
  Langfuse-versioned (`LangfusePromptDataset`), but the skill markdown
  (`data/campaign/skills/b2b_email_style.md`) is a plain `text.TextDataset`.
  Once `reflection` starts producing new skill versions we'll want to store
  the skill in Langfuse too (e.g. as a `text`-mode `LangfusePromptDataset`)
  so we get the same version history and rollback story as for prompts.
- **`evaluation` reuses cached emails instead of re-invoking the agent.** The
  experiment task is an in-memory lookup of
  `data/outputs/runs/{run_id}/emails/{case_id}.json`, not a call back into the
  `campaign` chain. This guarantees the demo UI and the scored output are
  byte-identical, and saves 20 LLM calls per evaluation run. Trade-off: the
  experiment doesn't capture per-item generation traces — those already exist
  in Langfuse from `campaign`. If we later want the experiment to be
  self-contained (e.g. to score a model we never ran via `campaign`), make the
  task call the LLM directly.
- **Per-case + aggregate scores are mirrored to disk** alongside the Langfuse
  dataset run (`data/outputs/runs/{run_id}/{per_case_scores,aggregate_scores}.json`).
  This is so `reflection` can read them off disk without a Langfuse round-trip,
  which keeps the demo working offline. Once `reflection` is in place we may
  switch to fetching scores straight from the Langfuse dataset run via its
  `dataset_run_id` (already captured in `aggregate_scores.json`) and drop the
  disk mirror.

## Where to look next

- [`DESIGN.md`](DESIGN.md) — full per-pipeline contract for all four pipelines,
  including the two that aren't built yet.
- `src/kedro_reflection_agent/data_models.py` — Pydantic models shared by the
  pipelines (`Customer`, `Product`, `EvalCase`, `Rubric`, `Email`, `JudgeScore`,
  `CaseScore`, `AggregateScore`, …).
- `src/kedro_reflection_agent/pipelines/_common.py` — the two shared helpers
  (`build_structured_chain`, `utc_now_iso`). Anything else copy-pasted between
  pipelines should be lifted here.
