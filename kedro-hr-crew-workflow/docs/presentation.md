![Kedro](./assets/kedro-horizontal-color-on-light.svg)

# Kedro + CrewAI: Production-Ready Agentic Workflows

**Overview:** This session is part of our Agentic Workflow series, explaining the feasibility and ease of integrating Kedro with CrewAI, an agentic framework. For prior demonstrations, see our earlier videos on integrations with LangGraph and Autogen.

## Production-Ready Agentic Workflows

### The Vision

Building robust, maintainable agentic workflows by combining:
- **Kedro**: Pipelines, catalogs, configuration, observability
- **CrewAI**: Agents, tasks, orchestrated workflows

### Key Principles

1. **Agentic ≠ Unstructured** — Agents thrive within a pipeline framework for maintainability and testability
2. **Configuration as Code** — Prompts & LLM settings live in YAML catalog; version in Git, A/B test freely
3. **Hybrid by Design** — Deterministic layers (parsing, reporting) + agentic layers (reasoning, evaluation)
4. **Observable & Traceable** — Kedro-Viz, preview functions, and optional tracing for full visibility

### Framework Landscape
- **LangGraph**: Graph-based state machines
- **AutoGen**: Multi-agent conversation patterns
- **CrewAI**: Role-based agents with defined tasks and crew orchestration

### Agentic Design Patterns

![Common Patterns](./assets/agentic_workflow_patterns.jpg)

---

## Architecture — Component Ownership

### Who Owns What?

| **Component** | **Kedro** | **CrewAI** |
|---|---|---|
| **Prompts & Config** | ✓ Catalog via `prompt datasets` | — |
| **Agent Context** | ✓ Built via `llm_context_node` | ✓ Consumes context |
| **Agents & Tasks** | — | ✓ Role, goal, tasks, execution |
| **Tools & Logic** | ✓ Catalog datasets | ✓ logic execution |
| **Pipeline Orchestration** | ✓ DAG execution and open to use any orchestrator | — |

### Maintainability Stack

- **Testability**: Each node is independent and unit-testable
- **Configuration**: No magic paths — all prompts in catalog YAML
- **Type Safety**: Pydantic for structured outputs
- **Observability**: Kedro-Viz for DAG visualization, `preview_fn` for data inspection, optional Langfuse/Opik integration

---

## Use Case — HR Candidate Screening

### The Problem
- **Scale**: Hundreds of resumes per role
- **Pain Point**: Manual screening is slow, inconsistent, and hard to audit
- **Requirement**: Structured evidence-based matching with clear recommendations

### The Solution

Extract and evaluate candidates using a **hybrid deterministic + agentic workflow**:

```
┌─────────────┐         ┌──────────────────────┐         ┌─────────────────┐
│ Job .docx   │ ────→   │ Parse & Structure    │ ────→   │ Job Metadata    │
│ Resume .docx│         │ (Deterministic)      │         │ Requirements    │
└─────────────┘         └──────────────────────┘         └─────────────────┘
       ↓                          ↓
       └──────────────────────────┴───────────────────────┐
                                  ↓
                    ┌──────────────────────────┐
                    │ Extract Evidence         │
                    │ Match & Evaluate         │
                    │ (Agentic Layer)          │
                    └──────────────────────────┘
                                  ↓
                    ┌──────────────────────────┐
                    │ Generate Report          │
                    │ Compose Email Draft      │
                    │ (Deterministic)          │
                    └──────────────────────────┘
                                  ↓
                    ┌──────────────────────────┐
                    │ HR Report + Email        │
                    └──────────────────────────┘
```

### Pipeline Stages
1. **Resume Parser Agent** — Extract experience, skills, education
2. **Requirements Matcher** — Evaluate fit against job requirements
3. **Resume Evaluator** — Detailed assessment and recommendation
4. **Reporting** — Generate audit trail and draft communications

---

## Live Demonstration

### Project Structure Overview
- `conf/`: Configuration (catalog, parameters, credentials, genai config)
- `data/`: Prompts, sample documents, outputs
- `src/`: Pipelines, datasets, and utilities (llm_context_node)

### What We'll See
1. **Kedro-Viz**: Interactive pipeline visualization (node coloring, preview_fn)
2. **Individual Pipeline Runs**: Each stage in isolation
3. **End-to-End Execution**: From raw documents to HR report
4. **Outputs**: Generated documents and structured data

---

## Roadmap — Production Readiness

### Immediate Improvements

- **Batch Processing**: Scale via PartitionedDataset and orchestrators
- **Evaluation Framework**: Dedicated evaluation nodes + metric tracking
- **Tracing & Monitoring**: Langfuse/Opik integration for observability
- **Scheduling**: Run via Airflow, Prefect, or event-driven architecture
- **Security**: Secrets management in `conf/local/`

*This project is developed with event-driven architecture in mind and can easily be extended to use batch processing*

### Kedro Evolution — What's Coming

| **Phase** | **Focus** |
|-----------|-----------|
| **Now** | Patterns and feedback from the community |
| **Next** | First-class evaluation support for agents/GenAI |
| **Future** | Streaming patterns for token/chunk streaming |

> You can adopt these patterns in your projects **right now**.

---

## Slide 6: Key Takeaways

✅ **Agentic + Structured = Best of Both Worlds**  
Combine agentic intelligence with Kedro's pipeline robustness

✅ **Configuration-Driven Development**  
Prompts, LLM settings, and workflows live in YAML — version, test, and audit in Git

✅ **Hybrid Workflows Pay Off**  
Deterministic stages handle parsing and reporting; agentic stages handle reasoning and evaluation

✅ **Production-Ready from Day One**  
Built-in support for observability, scaling, and orchestration

✅ **This Repository as Reference**  
Use the HR screening workflow as a blueprint for your own Kedro + CrewAI projects

---

## Slide 7: Questions?

**Thank you for your attention.**

Questions, feedback, and contributions welcome!
