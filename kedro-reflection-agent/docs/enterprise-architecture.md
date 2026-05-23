# Reflection Hub — Enterprise Architecture

> **Self-improving agent platform for telco.**  
> One platform investment, N business units. Governance built in. Value compounds as the portfolio grows.

---

## UI — Running Locally

All HTML prototypes live in `docs/ui/`. Start the dev server from the project root:

```bash
# Python (no install required)
python -m http.server 8080 --directory docs/ui

# or use the helper script
python docs/serve.py
```

Then open **http://localhost:8080/reflection-hub.html**

### Page Index

| Page | File | Description |
|---|---|---|
| Overview | `reflection-hub.html` | Portfolio dashboard — Issue Matrix, Success Matrix, KPIs |
| Sales | `sales.html` | B2B Sales agent — score progression, reflection timeline, audit |
| Marketing | `marketing.html` | Consumer Marketing agent — cross-transfer opportunity |
| Customer Support | `customer-support.html` | Care agent — rollback event, recovery, empathy scoring |
| Products | `products.html` | Product catalogue — per-product scores and flags |
| Teams | `teams.html` | Team cards, member assignments, agent status |
| Campaigns | `campaigns.html` | All run history — table and score chart |
| Review Center | `review-center.html` | Proposal review queue — grid cards, filters, bulk approve |
| Reflections | `reflections.html` | Reflection history — table, score trend, failure breakdown |
| Leaderboards | `leaderboards.html` | Podium, radar chart, dimension comparison |
| Insights | `insights.html` | AI intelligence summary, signal cards, trend charts |
| Reports | `reports.html` | Report templates, recent exports, schedule |
| Settings | `settings.html` | Platform config — General, Agents, Eval, Notifications, API |

---

## System Layers

```
                    ╔══════════════════════════════════════════════════════════════════════╗
                    ║              PORTFOLIO INTELLIGENCE LAYER                            ║
                    ║              Platform Team  ·  Leadership                            ║
                    ║                                                                      ║
                    ║  ┌──────────────────┐ ┌─────────────────┐ ┌──────────────────────┐   ║
                    ║  │ Quality Trend    │ │  Issue Matrix   │ │ Cross-Agent Learning │   ║
                    ║  │ per agent ·      │ │ failure types × │ │ match fixes across   │   ║
                    ║  │ rolling runs     │ │ business units  │ │ units; flag systemic │   ║
                    ║  └──────────────────┘ └─────────────────┘ └──────────────────────┘   ║
                    ║  ┌──────────────────────────────────────────────────────────────┐    ║
                    ║  │  Audit Roll-up · approvals · regressions · rollbacks         │    ║
                    ║  └──────────────────────────────────────────────────────────────┘    ║
                    ╚════════════╤══════════════════╤═══════════════════╤══════════════════╝
                     scores ↑    │      scores ↑    │     scores ↑      │
                     proposals ↓ │      proposals ↓ │     proposals ↓   │
        ┌────────────────────────▼──┐ ┌─────────────▼──────────────┐ ┌──▼─────────────────────────┐
        │      B2B SALES AGENT      │ │  CONSUMER MARKETING AGENT  │ │   CUSTOMER CARE AGENT      │
        │  Enterprise outreach      │ │  Plan & device offers      │ │   Support reply suggestions│
        │                           │ │                            │ │                            │
        │  ┌────────┐               │ │  ┌────────┐                │ │  ┌────────┐                │
        │  │Generate│               │ │  │Generate│                │ │  │Generate│                │
        │  └───┬────┘               │ │  └───┬────┘                │ │  └───┬────┘                │
        │      ▼                    │ │      ▼                     │ │      ▼                     │
        │  ┌──────────┐             │ │  ┌──────────┐              │ │  ┌──────────┐              │
        │  │ Evaluate │             │ │  │ Evaluate │              │ │  │ Evaluate │              │
        │  └───┬──────┘             │ │  └───┬──────┘              │ │  └───┬──────┘              │
        │      ▼                    │ │      ▼                     │ │      ▼                     │
        │  ┌─────────┐              │ │  ┌─────────┐               │ │  ┌─────────┐               │
        │  │ Reflect │              │ │  │ Reflect │               │ │  │ Reflect │               │
        │  └───┬─────┘              │ │  └───┬─────┘               │ │  └───┬─────┘               │
        │      ▼                    │ │      ▼                     │ │      ▼                     │
        │  ┌─────────┐              │ │  ┌─────────┐               │ │  ┌─────────┐               │
        │  │ Propose │              │ │  │ Propose │               │ │  │ Propose │               │
        │  └───┬─────┘              │ │  └───┬─────┘               │ │  └───┬─────┘               │
        │      ▼                    │ │      ▼                     │ │      ▼                     │
        │  ┌────────────────────┐   │ │  ┌────────────────────┐    │ │  ┌────────────────────┐    │
        │    ✋ Human Approval             ✋ Human Approval              ✋ Human Approval        |
        │  └───┬────────────────┘   │ │  └───┬────────────────┘    │ │  └───┬────────────────┘    │
        │      ▼                    │ │      ▼                     │ │      ▼                     │
        │  ┌────────┐               │ │  ┌────────┐                │ │  ┌────────┐                │
        │  │ Apply  │               │ │  │ Apply  │                │ │  │ Apply  │                │
        │  └────────┘               │ │  └────────┘                │ │  └────────┘                │
        └───────────────────────────┘ └────────────────────────────┘ └────────────────────────────┘
                    │                              │                              │
                    └──────────────────────────────┼──────────────────────────────┘
                                                   │
                    ╔══════════════════════════════▼════════════════════════════════════════╗
                    ║                   SHARED PLATFORM SERVICES                            ║
                    ║                                                                       ║
                    ║  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────┐    ║
                    ║  │   Prompt Registry   │  │  Skill Library   │  │  Eval Framework│    ║
                    ║  │  Langfuse · versioned  │  markdown · v'd  │  │  judge+heurist.│    ║
                    ║  └─────────────────────┘  └──────────────────┘  └────────────────┘    ║
                    ║  ┌─────────────────────┐  ┌──────────────────┐  ┌────────────────┐    ║
                    ║  │    Audit Log        │  │   Orchestration  │  │  Regression    │    ║
                    ║  │  append-only · JSON │  │      Kedro       │  │  Test Bank     │    ║
                    ║  └─────────────────────┘  └──────────────────┘  └────────────────┘    ║
                    ╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Portfolio Intelligence — What It Surfaces

| View | Question answered | UI Page | Audience |
|---|---|---|---|
| **Quality Trend** | Who's improving, who's stalling, who's regressing? | `leaderboards.html` | Leadership |
| **Issue Matrix** | Which failure modes are unit-specific vs. systemic across all three? | `reflection-hub.html` | Platform team |
| **Cross-Agent Learnings** | When a fix in one unit matches an open failure in another, should it travel? | `insights.html` | Platform team |
| **Audit Roll-up** | What changed, when, who approved it, any rollbacks? | `reflections.html` | Governance / Compliance |

---

## Agent Loop — Invariant Shape

Every agent follows the same six-step loop. Adding a fourth agent is a configuration exercise, not an engineering project.

| Step | What happens | UI touchpoint |
|---|---|---|
| **Generate** | Agent drafts its work (emails, offers, reply suggestions) against live targets | `campaigns.html` |
| **Evaluate** | LLM judge + deterministic heuristics score each output against domain rubric | `sales.html` / domain pages |
| **Reflect** | Meta-agent reads scores + worst cases and proposes improvements | `reflections.html` |
| **Propose** | Improved system prompt, updated skill file, new regression cases written to disk | `review-center.html` |
| **Human Approval** | Platform/domain reviewer inspects the diff before anything goes live | `review-center.html` |
| **Apply** | Approved changes versioned into Langfuse; local files synced; audit row appended | `reflections.html` (audit trail) |

---

## Shared Platform Services

| Service | Technology | Role |
|---|---|---|
| **Prompt Registry** | Langfuse (versioned) | Source of truth for all system prompts; supports rollback |
| **Skill Library** | Markdown files (versioned on disk) | Style guides injected at runtime per agent |
| **Evaluation Framework** | LLM judge + heuristic scorers | Shared infrastructure; per-agent judge config and dimensions — see note below |
| **Orchestration** | Kedro pipelines | Deterministic, auditable pipeline runs |
| **Audit Log** | Append-only JSON | Every apply event recorded with timestamp and reviewer |
| **Regression Test Bank** | Per-agent eval datasets (Langfuse) | Grows automatically; failures in one unit become permanent tests |

### Evaluation Framework — Two Levels of Rubric

The framework has **two distinct layers** that are often conflated:

**1. Shared infrastructure (identical across all agents)**

- `run_experiment()` Langfuse experiment runner
- Kedro evaluation pipeline shape and catalog pattern
- Heuristic scorer scaffold (4 pluggable slots)
- `AggregateScore` / `CaseScore` disk output schema

**2. Per-agent configuration (swapped at deploy time via `parameters.yml`)**

| Config | What changes | Example |
|---|---|---|
| `judge_prompt` label | The LLM judge's scoring criteria and dimension definitions | B2B: writing quality, personalisation, groundedness · Care: empathy opener, resolution clarity, escalation avoidance |
| `_JUDGE_NAMES` | The scorer names written to Langfuse and used in aggregation | `("writing_quality", "personalization", "groundedness")` → `("empathy", "resolution_clarity", "tone")` |
| Heuristic impls | Domain-specific structural checks | B2B: `subject_present`, `no_fake_skus` · Care: `empathy_opener_present`, `no_escalation_language` |
| Eval dataset | Separate Langfuse dataset per agent | `b2b_sales_eval` · `consumer_mktg_eval` · `customer_care_eval` |

**3. Per-case rubric (carried on every individual eval case)**

Each case in the Langfuse dataset includes a `rubric` field the judge and heuristics read at runtime:

```json
{
  "required_mentions": ["fleet management", "uptime SLA"],
  "forbidden_mentions": ["generic connectivity"],
  "expected_cta": "demo",
  "expected_tone": "consultative"
}
```

This enforces case-specific expectations *within* an agent's run without changing the pipeline code.

**Design intent:** the pipeline code does not change when adding a new agent. Only the Langfuse prompt label, scorer names, and heuristic implementations are swapped via config. The scoring contract (how results are stored, aggregated, and handed to the meta-agent) is invariant.

---

## Why This Architecture

**Scale** — One platform investment serves N business units. Evaluation, governance, and audit are not rebuilt per team.

**Governance built in** — No change touches production without a human approval gate. Every version is traceable.

**Compounding value** — A failure caught in one unit becomes a regression test there *and* surfaces an opportunity for the others. The platform gets smarter as the portfolio grows.

---

## File Layout (As of now)

```
docs/
├── enterprise-architecture.md   ← this file
├── serve.py                     ← dev server helper
└── ui/                          ← all HTML prototypes
    ├── reflection-hub.html      ← entry point / portfolio overview
    ├── sales.html
    ├── marketing.html
    ├── customer-support.html
    ├── products.html
    ├── teams.html
    ├── campaigns.html
    ├── review-center.html
    ├── reflections.html
    ├── leaderboards.html
    ├── insights.html
    ├── reports.html
    ├── settings.html
    └── enterprise-architecture.md
```

---

## Current Status

| Milestone | Status |
|---|---|
| Per-agent loop (B2B Sales) — end-to-end | ✅ Working |
| Consumer Marketing agent | ⬜ Next |
| Customer Care agent | ⬜ Next |
| Portfolio Intelligence layer | ⬜ Next |
| Cross-agent learning engine | ⬜ Next |
| UI prototype — all 13 pages | ✅ Complete (`docs/ui/`) |
