# Reflection Hub with Kedro

## Agenda

| # | Segment | What you will see |
|---|---------|-------------------|
| **1** | **Introduction** | The business problem and the reusable improvement lifecycle |
| **2** | **How it's built** | Project structure, sample data, and Kedro configuration |
| **3** | **Live demo — B2B Sales** | Full agent loop running in the Reflection Hub UI |
| **4** | **Org Overview** | Portfolio view across all three agents — scores, trends, cross-agent patterns |
| **5** | **Wrap-up** | Key takeaways and what Kedro brings to agentic systems |
| **6** | **Q&A** | Open discussion |

---

## Kedro features in this project

| Feature | Role |
|---------|------|
| **`llm_context_node` + `LLMContext`** | Standard way to wire LLM + prompts into pipeline nodes |
| **`LangfusePromptDataset`** | Versioned prompts in Langfuse with local disk cache |
| **`LangfuseTraceDataset`** | One observability trace per agent generation |
| **`ChatOpenAIDataset`** | LLM configuration and credentials via the catalog |
| **`RunIndexHook`** | Cross-run audit index powering the Org Overview |
| **Runtime parameters** | `agent_id`, `run_id` — same pipelines, multiple agents and runs |
| **Pipeline modularity** | Five independent pipelines with clear boundaries |
| **Kedro-Viz** | Pipeline graph visible inside the demo UI |
