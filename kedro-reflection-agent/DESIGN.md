# kedro-reflection-agent — design

Working document. Captures the agreed shape of the demo before implementation.
Updated slice by slice.

---

## What this demo shows

A B2B campaign agent (telco sales) that writes personalised outreach emails,
seeded deliberately mediocre, then improves itself by reflecting on its own
outputs. One open-loop reflection cycle. The same loop trivially extends to
cross-sell, pricing, or any other agent — different agent, same pipelines.

## The flow

```
                        ┌──────────────┐
   seed + prompt +  ──▶ │  agent_run   │ ──▶ emails (disk) + traces (Langfuse)
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
`agent_run (run_1) → evaluation (run_1) → reflection → apply → agent_run (run_2) → evaluation (run_2)`.

---

## Pipelines

### 1. `agent_run`

For each eval case (customer × product), generate one outreach email and emit
one trace to Langfuse so downstream scoring can find it.

| Inputs                                                    | Source                                           |
| --------------------------------------------------------- | ------------------------------------------------ |
| 10 customers                                              | `data/seed/customers.json`                       |
| 5 products                                                | `data/seed/products.json`                        |
| 20 eval cases (each = customer_id + product_id + rubric)  | `data/agent_run/eval_cases.json` ↔ Langfuse      |
| System prompt (current version)                           | `data/agent_run/prompts/system_prompt.json` ↔ Langfuse |
| Skill file (current version)                              | `data/agent_run/skills/b2b_email_style.md` (disk) |
| `run_id` (runtime param)                                  | CLI / Streamlit                                  |

| Outputs                                                                   | Destination                                                     |
| ------------------------------------------------------------------------- | --------------------------------------------------------------- |
| 20 emails (subject, body, metadata)                                       | `data/outputs/runs/{run_id}/emails/{case_id}.json`              |
| Run metadata (prompt version, skill version, model, timestamp, count)     | `data/outputs/runs/{run_id}/run_metadata.json`                  |
| One trace per case                                                        | Langfuse                                                        |

### 2. `evaluation`

For a given `run_id`, fetch traces back, run heuristic + LLM-judge scorers
against each email using the rubric attached to its eval case, then aggregate.

| Inputs                                          | Source                                                                  |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Run's traces (or emails on disk as fallback)    | Langfuse / `data/outputs/runs/{run_id}/emails/`                         |
| Eval cases (for the rubrics)                    | reuse from `agent_run`                                                  |
| Judge prompt                                    | `data/evaluation/prompts/judge_prompt.json` ↔ Langfuse                  |
| `run_id` (runtime param)                        | CLI / Streamlit                                                         |

| Outputs                                                          | Destination                                                |
| ---------------------------------------------------------------- | ---------------------------------------------------------- |
| Per-case scores                                                  | `data/outputs/runs/{run_id}/per_case_scores.json`          |
| Aggregate scores (mean per scorer, mean total, n_passing)        | `data/outputs/runs/{run_id}/aggregate_scores.json`         |
| Scores attached back to traces (optional)                        | Langfuse                                                   |

**Scorers (7 total):**

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
| Current system prompt + skill file           | reuse from `agent_run`                                          |
| Current eval cases                           | reuse from `agent_run`                                          |
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
| New skill → disk                                                     | `data/agent_run/skills/b2b_email_style.md` (overwritten)     |
| New eval cases → Langfuse evaluation dataset                         | Langfuse                                                     |
| Audit row (`reflection_id`, timestamp, applied artifacts, prev versions) | `data/outputs/apply_history.json` (append)               |

After `apply`, re-running `agent_run` reads the new live state and produces `run_2`.

---

## Conventions

- **`run_id`** identifies one execution of `agent_run` + `evaluation`. Demo uses
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
