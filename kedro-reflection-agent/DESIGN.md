# kedro-reflection-agent — design

Working document. Captures the agreed shape of the demo and tracks what has
been implemented so far. Updated slice by slice.

## Implementation status

| Pipeline     | Status            | Notes                                                   |
| ------------ | ----------------- | ------------------------------------------------------- |
| `campaign`   | implemented       | 3 nodes; produces emails + run metadata, traces Langfuse |
| `evaluation` | implemented       | 5 nodes; drives Langfuse `run_experiment(...)`           |
| `reflection` | skeleton (catalog stub + empty `pipeline.py`) | next slice                                 |
| `apply`      | skeleton (catalog stub + empty `pipeline.py`) | follows `reflection`                       |
| Streamlit UI | scaffold (`app/main.py`, `app/components/`)   | wires up after `apply`                     |

Seed and evaluation data (10 customers, 5 products, 20 campaign targets,
20 eval cases) are committed under `data/`. See README for the layout.

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
   skill + eval cases   └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
   traces + scores  ──▶ │ evaluation   │ ──▶ per-case scores + aggregate (disk)
   + judge prompt       └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
   current prompt + ──▶ │ reflection   │ ──▶ proposal: summary + new prompt
   skill + eval cases   └──────────────┘     + new skill + new eval cases (disk)
   + traces + scores            │
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
outreach email per target and emit one Langfuse trace per generation. Owns no
evaluation concerns — it reads its own `targets` list and does not see the
evaluation dataset. The two share a `case_id` namespace by convention so
evaluation can join emails to rubrics.

| Inputs                                                    | Source                                           |
| --------------------------------------------------------- | ------------------------------------------------ |
| 10 customers                                              | `data/seed/customers.json`                       |
| 5 products                                                | `data/seed/products.json`                        |
| 20 campaign targets (case_id + customer_id + product_id)  | `data/campaign/targets.json`                     |
| System prompt (current version)                           | `data/campaign/prompts/system_prompt.json` ↔ Langfuse |
| Skill file (current version)                              | `data/campaign/skills/b2b_email_style.md` (disk) |
| `run_id` (runtime param)                                  | CLI / Streamlit                                  |

| Outputs                                                                   | Destination                                                     |
| ------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 20 emails (subject, body, metadata)                                       | `data/outputs/runs/{run_id}/emails/{case_id}.json`              |
| Run metadata (prompt version, skill version, model, timestamp, count)     | `data/outputs/runs/{run_id}/run_metadata.json`                  |
| One trace per case                                                        | Langfuse                                                        |

### 2. `evaluation`

Drives a Langfuse `DatasetClient.run_experiment(...)` over the evaluation
dataset. For a given `run_id`, the experiment task is a disk lookup of the
campaign-generated email for each case_id (no LLM call inside the task);
evaluators score those outputs.

Why a Langfuse experiment rather than a hand-rolled scoring loop:

- Successive experiments (before reflection, after reflection) are tracked as
  named dataset runs in Langfuse and trivially comparable in the UI.
- Each evaluator emits a typed Langfuse `Evaluation` (name + value + comment)
  that is stored against the experiment item and visible in the dashboard.
- The pattern mirrors `kedro-agentic-workflows` (the source-of-truth project),
  keeping the two demos architecturally aligned.

The task **looks up the cached campaign email** rather than re-invoking the
agent. This gives the demo a single source of truth — the email shown in the
UI is byte-identical to the one being scored — and saves 20 LLM calls per
evaluation run. The price is that the experiment doesn't capture per-item
generation traces; those already exist in Langfuse from running `campaign`.

| Inputs                                          | Source                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Eval cases (owns the dataset; provides rubrics) | `data/evaluation/eval_cases.json` ↔ Langfuse                            |
| Customers, products (seed)                      | `data/seed/` (re-used catalog entries)                                  |
| Campaign emails (looked up by `case_id`)        | `data/outputs/runs/{run_id}/emails/`                                    |
| Judge prompt                                    | `data/evaluation/prompts/judge_prompt.json` ↔ Langfuse                  |
| Judge LLM                                       | `gpt-4o` @ temperature 0 (bigger than the campaign LLM for steadiness)  |
| `run_id`, `model_name`, `system_prompt_version`, `judge_model_name`, `judge_prompt_version`, `passing_threshold`, `body_length_min`, `body_length_max` (runtime params) | CLI / Streamlit |

| Outputs                                                          | Destination                                                |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| Dataset run + per-item evaluations + per-item traces             | Langfuse (named `campaign_{run_id}_prompt_v{N}`)           |
| Per-case scores (Langfuse → disk mirror, for reflection)         | `data/outputs/runs/{run_id}/per_case_scores.json`          |
| Aggregate scores (mean per scorer, mean total, n_passing, urls)  | `data/outputs/runs/{run_id}/aggregate_scores.json`         |

**Scorers (7 total).** Five evaluator callables produce all seven `Evaluation`s:
four heuristic evaluators (one each) and one combined LLM-judge evaluator that
does a single structured LLM call per email and returns a `list[Evaluation]` of
three dimensions (writing_quality, personalization, groundedness). 20 judge
LLM calls per evaluation run, not 60. The per-case mean is the equal-weighted
mean across all seven; cases with mean ≥ `passing_threshold` (default 0.92,
tuned so the v0 baseline pass rate leaves room for reflection to improve it)
count as passing.

| Scorer              | Type        | What it checks                                                     |
| ------------------- | ----------- | ------------------------------------------------------------------ |
| `subject_present`   | heuristic   | non-empty subject line parsed out                                  |
| `length_in_range`   | heuristic   | body length within `[min, max]` chars                              |
| `no_fake_skus`      | heuristic   | nothing matches `\b[A-Z]{2,}[-]?\d+` outside known product names   |
| `cta_present`       | heuristic   | matches CTA patterns (meeting / demo / call / reply)               |
| `writing_quality`   | LLM-judge   | clarity, grammar, tone match                                       |
| `personalization`   | LLM-judge   | uses customer industry / size / tenure / current products          |
| `groundedness`      | LLM-judge   | claims only what the product card supports                         |

### 3. `reflection`

Meta-agent reads the current artifacts + the failures, and proposes a new set:
narrative summary, better system prompt, updated skill file, and new eval cases
derived from the failures (so weaknesses become permanent regression cases).

| Inputs                                       | Source                                                          |
| -------------------------------------------- | --------------------------------------------------------------- |
| Current system prompt + skill file           | reuse from `campaign`                                           |
| Current eval cases                           | reuse from `evaluation`                                         |
| Traces + scores from latest run              | Langfuse + `data/outputs/runs/{run_id}/`                        |
| Meta-agent prompt                            | `data/reflection/prompts/meta_agent_prompt.json` ↔ Langfuse     |
| `run_id`, `reflection_id` (runtime params)   | CLI / Streamlit                                                 |

| Outputs                                                          | Destination                                                            |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Narrative summary (`identified` / `fixed` / `reasons`)           | `data/outputs/reflections/{reflection_id}/summary.md`                  |
| Proposed system prompt (new version, not yet applied)            | `data/outputs/reflections/{reflection_id}/proposed_prompt.json`        |
| Proposed skill file (new content, not yet applied)               | `data/outputs/reflections/{reflection_id}/proposed_skill.md`           |
| Proposed new eval cases                                          | `data/outputs/reflections/{reflection_id}/proposed_eval_cases.json`    |

Reflection is open-loop: it never writes to the live prompt / skill / dataset.
Only `apply` does that.

### 4. `apply`

Take an approved `reflection_id` and commit its three artifacts to the live
locations, then append an audit row.

| Inputs                                          | Source                                                |
| ----------------------------------------------- | ----------------------------------------------------- |
| Proposed prompt / skill / eval cases            | `data/outputs/reflections/{reflection_id}/`           |
| `reflection_id` (runtime param)                 | CLI / Streamlit                                       |

| Outputs                                                              | Destination                                                  |
| -------------------------------------------------------------------- | ------------------------------------------------------------ |
| New system prompt → Langfuse (new version)                           | Langfuse                                                     |
| New skill → disk                                                     | `data/campaign/skills/b2b_email_style.md` (overwritten)      |
| New eval cases → Langfuse evaluation dataset                         | Langfuse                                                     |
| Audit row (`reflection_id`, timestamp, applied artifacts, prev versions) | `data/outputs/apply_history.json` (append)               |

After `apply`, re-running `campaign` reads the new live state and produces `run_2`.

---

## Conventions

- **`run_id`** identifies one execution of `campaign` + `evaluation`. Demo uses
  `run_1` (before reflection) and `run_2` (after).
- **`reflection_id`** identifies one execution of `reflection`. Demo uses
  `refl_1`.
- **Langfuse-backed datasets** (prompt, eval dataset, traces) use the
  experimental `LangfusePromptDataset` / `LangfuseEvaluationDataset` /
  `LangfuseTraceDataset` with `sync_policy: local` so they cache to disk and
  work offline. Push happens via `apply`.
- **Data models** (`Customer`, `Product`, `EvalCase`, `Rubric`, `Email`, `Score`,
  `ReflectionProposal`, …) live in `src/kedro_reflection_agent/data_models.py`.
  They are added incrementally — each iteration introduces only the models it
  needs, refining earlier ones as required.

---

## Out of scope

- Real telco data (use synthetic)
- Closed-loop auto-apply (we stay open-loop with one-keystroke approval)
- Ontology / graph updates (next iteration)
- Production-grade error handling, multi-tenancy, deployment
