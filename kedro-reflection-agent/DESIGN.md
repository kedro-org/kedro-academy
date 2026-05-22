# kedro-reflection-agent — design

Working document. Captures the agreed shape of the demo and tracks what has been implemented. Updated slice by slice.

## Implementation status

| Pipeline     | Status       | Notes                                                              |
| ------------ | ------------ | ------------------------------------------------------------------ |
| `campaign`   | ✅ complete  | 3 nodes; produces emails + run metadata; traces every generation   |
| `evaluation` | ✅ complete  | 5 nodes; drives Langfuse `run_experiment(...)`; 7 scorers          |
| `reflection` | ✅ complete  | 3 nodes; meta-agent proposes prompt + skill + eval cases           |
| `apply`      | ✅ complete  | 1 node; commits proposal; appends audit row                        |
| Streamlit UI | ✅ complete  | 3-step interactive demo with Kedro-Viz + Langfuse observability    |

---

## What this demo shows

A B2B campaign agent (telco sales) that writes personalised outreach emails,
seeded deliberately mediocre, then improves itself by reflecting on its own
outputs. One open-loop reflection cycle. The same loop trivially extends to
cross-sell, pricing, or any other agent — different agent, same pipelines.

## The flow

```
                        ┌──────────────┐
   seed + prompt +  ──▶ │  campaign    │ ──▶ emails (disk) + traces (Langfuse)
   skill + targets      └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
   emails + rubrics ──▶ │ evaluation   │ ──▶ per-case scores + aggregate (disk)
   + judge prompt       └──────────────┘     + named dataset run (Langfuse)
                                │
                                ▼
                        ┌──────────────┐
   current prompt + ──▶ │ reflection   │ ──▶ proposal: summary + new prompt
   skill + failing      └──────────────┘     + new skill + new eval cases (disk)
   cases + scores               │
                                ▼
                        ┌──────────────┐
   approved proposal ─▶ │   apply      │ ──▶ new prompt → Langfuse,
                        └──────────────┘     new skill → disk,
                                             new eval cases → Langfuse,
                                             audit row appended
```

Two runs of the first two pipelines bracket one reflection cycle:
`campaign (run_1) → evaluation (run_1) → reflection → apply → campaign (run_2) → evaluation (run_2)`.

---

## Pipelines

### 1. `campaign`

Given a list of campaign targets (customer × product pairs), generate one
outreach email per target and emit one Langfuse trace per generation.

| Inputs                                                   | Source                                                |
| -------------------------------------------------------- | ----------------------------------------------------- |
| 10 customers                                             | `data/seed/customers.json`                            |
| 5 products                                               | `data/seed/products.json`                             |
| Campaign targets (case_id + customer_id + product_id)    | `data/campaign/targets.json`                          |
| System prompt (current version)                          | `data/campaign/prompts/system_prompt.json` ↔ Langfuse |
| Skill file (current version)                             | `data/campaign/skills/b2b_email_style.md`             |
| `run_id`, `model_name`, `system_prompt_version`          | CLI / Streamlit                                       |

| Outputs                                               | Destination                                              |
| ----------------------------------------------------- | -------------------------------------------------------- |
| Emails (subject, body, metadata)                      | `data/outputs/runs/{run_id}/emails/{case_id}.json`       |
| Run metadata (model, versions, counts, timestamps)    | `data/outputs/runs/{run_id}/run_metadata.json`           |
| One trace per case                                    | Langfuse (trace name `campaign:{case_id}`)               |

**Node topology:**

```
llm_context_node            ->  agent_context (LLMContext)
prepare_agent_inputs_node   ->  agent_inputs  (list[{case_id, customer, product}])
generate_emails_node        ->  emails, run_metadata
```

The chain is `ChatPromptTemplate | LLM.with_structured_output(EmailOutput)`.
The skill markdown is injected via `{skill}` in the system prompt template.
Each invocation passes `run_name=f"campaign:{case_id}"` so Langfuse traces are
named per-case and can be located by name in the API.

---

### 2. `evaluation`

Drives a Langfuse `DatasetClient.run_experiment(...)` over the evaluation dataset.
The experiment task is a **disk lookup** of the campaign email by `case_id` (no
LLM call inside the task), so what is scored is byte-identical to what the UI shows.

| Inputs                                                  | Source                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------- |
| Eval cases (owns the dataset; provides rubrics)         | `data/evaluation/eval_cases.json` ↔ Langfuse                              |
| Customers, products                                     | `data/seed/` (shared catalog entries)                                     |
| Campaign emails (looked up by `case_id`)                | `data/outputs/runs/{run_id}/emails/`                                      |
| Judge prompt                                            | `data/evaluation/prompts/judge_prompt.json` ↔ Langfuse                    |
| `run_id`, `judge_model_name`, `judge_prompt_version`, `passing_threshold`, `body_length_min/max` | CLI / Streamlit |

| Outputs                                                         | Destination                                                |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| Dataset run + per-item evaluations + per-item traces            | Langfuse (run name `campaign_{run_id}_prompt_v{N}`)        |
| Per-case scores (case_id, evaluations, mean_score, passing)     | `data/outputs/runs/{run_id}/per_case_scores.json`          |
| Aggregate scores (mean per scorer, pass_rate, n_passing, urls)  | `data/outputs/runs/{run_id}/aggregate_scores.json`         |

**Node topology:**

```
judge_context_node              ->  judge_context
init_heuristic_evaluators_node  ->  heuristic_evaluators (4 callables)
init_judge_evaluator_node       ->  judge_evaluator (1 callable → 3 Evaluations)
make_campaign_task_node         ->  campaign_task (closure over emails dict)
run_experiment_node             ->  per_case_scores, aggregate_scores
```

**Scorers (7 total):**

| Scorer            | Type      | What it checks                                               |
| ----------------- | --------- | ------------------------------------------------------------ |
| `subject_present` | heuristic | non-empty subject line present                               |
| `length_in_range` | heuristic | body length within `[min, max]` chars                        |
| `no_fake_skus`    | heuristic | no `\b[A-Z]{2,}[-]?\d+` outside known product names         |
| `cta_present`     | heuristic | matches CTA patterns (meeting / demo / call / reply)         |
| `writing_quality` | LLM-judge | clarity, grammar, tone                                       |
| `personalization` | LLM-judge | uses customer industry / size / tenure / current products    |
| `groundedness`    | LLM-judge | claims only what the product card supports                   |

One judge LLM call per email returns all three judge dimensions. Per-case mean is
equal-weighted across all 7; cases with mean ≥ `passing_threshold` count as passing.

---

### 3. `reflection`

Meta-agent reads the current artifacts + failing cases and proposes a replacement
set. Reflection is **open-loop** — it never writes to the live prompt, skill, or
dataset. Only `apply` does that.

| Inputs                                           | Source                                                      |
| ------------------------------------------------ | ----------------------------------------------------------- |
| Current system prompt                            | reuse from `campaign` catalog                               |
| Current skill file                               | reuse from `campaign` catalog                               |
| Current eval cases                               | reuse from `evaluation` catalog                             |
| Per-case scores + aggregate                      | `data/outputs/runs/{run_id}/per_case_scores.json`           |
| Meta-agent prompt                                | `data/reflection/prompts/meta_agent_prompt.json` ↔ Langfuse |
| `run_id`, `reflection_id`, `passing_threshold`   | CLI / Streamlit                                             |

| Outputs                                                        | Destination                                                         |
| -------------------------------------------------------------- | ------------------------------------------------------------------- |
| Narrative summary (`identified` / `fixed` / `reasons`)         | `data/outputs/reflections/{reflection_id}/summary.md`               |
| Proposed system prompt (new messages, not yet applied)         | `data/outputs/reflections/{reflection_id}/proposed_prompt.json`     |
| Proposed skill file (new content, not yet applied)             | `data/outputs/reflections/{reflection_id}/proposed_skill.md`        |
| Proposed new eval cases (from failure modes)                   | `data/outputs/reflections/{reflection_id}/proposed_eval_cases.json` |

**Node topology:**

```
meta_agent_context_node         ->  meta_agent_context
prepare_reflection_context_node ->  reflection_context (template vars)
reflect_node                    ->  reflection_summary, proposed_prompt,
                                    proposed_skill, proposed_eval_cases
```

**Key implementation details:**

- `prepare_reflection_context` filters out cases that errored in the Langfuse
  experiment (no local email generated — detected by empty `output.body`).
- If no cases fail the threshold, the N lowest-scoring cases are used instead
  so the meta-agent always has something to work with.
- Only the system message is extracted from the current prompt template and
  passed to the meta-agent (not the human message), to avoid duplicate content
  in the proposal.
- `proposed_prompt` is saved as a plain `json.JSONDataset` (list of
  `{role, content}` dicts) rather than a `LangfusePromptDataset` so `apply`
  can read it without an active Langfuse connection.

---

### 4. `apply`

Takes an approved `reflection_id` and commits all three artifacts to their live
locations, then appends an audit row.

| Inputs                                     | Source                                            |
| ------------------------------------------ | ------------------------------------------------- |
| Proposed prompt / skill / eval cases       | `data/outputs/reflections/{reflection_id}/`       |
| `reflection_id`                            | CLI / Streamlit                                   |

| Outputs                                                             | Destination                                             |
| ------------------------------------------------------------------- | ------------------------------------------------------- |
| New system prompt (new Langfuse version)                            | Langfuse (`b2b-email-system-prompt`)                    |
| New skill file                                                      | `data/campaign/skills/b2b_email_style.md` (overwritten) |
| New eval cases                                                      | Langfuse dataset `b2b-campaign-agent-eval`              |
| Audit row (reflection_id, timestamp, messages, skill, case ids)     | `data/outputs/apply_history.json` (append)              |

**Node topology:**

```
commit_reflection_node  ->  system_prompt, skill_text, eval_cases, apply_history
```

After `apply`, re-running `campaign` (with `run_id=run_2`) reads the new live
prompt and skill and produces `run_2` emails scored against the augmented eval set.

---

## Streamlit dashboard

Three-step interactive UI at `app/main.py`. Each step maps to one component file.

| Step  | File                          | Pipelines triggered           | Key panels                                    |
| ----- | ----------------------------- | ----------------------------- | --------------------------------------------- |
| 1     | `app/components/step_1_run.py`   | `campaign` + `evaluation`     | Run logs · Scoreboard · Langfuse              |
| 2     | `app/components/step_2_reflect.py` | `reflection` + `apply`      | Run logs · Proposal · Langfuse                |
| 3     | `app/components/step_3_rerun.py`  | `campaign` + `evaluation`    | Run logs · Compare (before/after) · Langfuse  |

**State machine** (`app/state.py`):

```
idle → run_1_done → reflected → applied → run_2_done
```

State is persisted to `data/demo_state.json`. The seed script writes a fresh
`seed_at` timestamp on reset; `main.py` detects this and calls
`st.cache_data.clear()` so stale cached data from the previous run is discarded.

**Langfuse observability panel** (`app/embeds.py` + `app/langfuse_analytics.py`):

Each step has a Langfuse tab that shows — when credentials are configured:
- Metrics row: total traces, LLM cost today, observations today
- Score averages bar chart (all 7 dimensions) from `/api/public/scores`
- Token usage by model from `/api/public/metrics`
- Daily traces + daily cost from `/api/public/metrics/daily`
- Recent traces expander with deep-links (requires `project_id` in credentials)

---

## Conventions

- **`run_id`** identifies one execution of `campaign` + `evaluation`. Demo uses
  `run_1` (before reflection) and `run_2` (after).
- **`reflection_id`** identifies one execution of `reflection`. Demo uses `refl_1`.
- **Catalog split by pipeline.** Each pipeline has its own
  `conf/base/catalog_{pipeline}.yml`. Shared/in-memory datasets use the
  `{default_dataset}` pattern in `conf/base/catalog.yml`.
- **Langfuse-backed datasets** use `sync_policy: local` so they cache to disk
  and work offline. Push to Langfuse happens through `apply`.
- **Scores computed locally.** The UI always filters `per_case_scores.json` to
  locally generated email IDs (not the full Langfuse experiment dataset) to
  avoid inflated metrics from experiment scaffolding items.
- **Data models** live in `src/kedro_reflection_agent/data_models.py` and are
  added incrementally as each pipeline slice is built.

---

## Out of scope

- Real telco data (use synthetic)
- Closed-loop auto-apply (open-loop with one-keystroke approval)
- Multi-turn conversation agent (single-shot generation per case)
- Production-grade error handling, multi-tenancy, deployment
