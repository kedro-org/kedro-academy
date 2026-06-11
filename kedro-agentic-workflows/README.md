# kedro-agentic-workflows

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

## 🌟 Overview

This project is a reference implementation demonstrating how `LangGraph` and `Kedro` can be combined to build agentic workflows for real-world applications.  

The use case focuses on **Customer Support Automation with Knowledge Base Integration** for an insurance company. It automates insurance customer support by combining intent detection, knowledge base retrieval, and personalized response generation, enabling more accurate and context-aware responses.

### Agentic Workflows
- **Intent Detection:** Classifies queries (general questions, new/existing claims, clarifications) and asks follow-ups if needed.  
- **Response Generation:** Retrieves relevant information from claims and documentation to generate responses, escalating unresolved issues automatically. Tool usage (e.g., KB lookup, claim retrieval/creation) is dynamically determined.

### Kedro + LangGraph
- **Kedro:** Manages data access and credentials, conversation history, sessions, and logs interactions for reproducibility and evaluation.  
- **LangGraph:** Orchestrates workflows, routing between intent detection, clarifications, tool use, and response generation.

### Required Data
- Product FAQs, help articles, and insurance manuals  
- Customer query transcripts (synthetic or anonymized)  
- Historical claims with descriptions, solutions, and statuses

## 🎯 Purpose of the Project

This project demonstrates how to build robust agentic workflows using `LangGraph` and `Kedro`. Specifically, it showcases:

* **Structuring conversational logic** – Breaking down multi-turn conversations into `LangGraph` nodes and agent states.
* **Dynamic tool selection** – Agents autonomously choose the appropriate tool (e.g., knowledge base lookup, claim creation) based on user intent.
* **Memory and state management** – Multi-turn conversation state is persisted using `LangGraph` checkpoints and `Kedro` datasets, enabling context-aware responses.
* **Knowledge base integration** – Claims and internal docs are ingested and used as tools for reasoning.
* **Secure credential handling** – Sensitive information (API keys, DB credentials) is managed securely through `Kedro` configurations.
* **Structured and reproducible outputs** – Agent responses include message content plus metadata, all logged for auditing and reproducibility.
* **Session logging** – Conversations, messages, and tool interactions are persisted to a database for auditing and analysis.
* **Observability and prompt tracking** – Integrates with external tools like `Langfuse` and `Opik` to track prompts, tool usage, and workflow execution.
* **Dataset-based evaluation** – Runs the agent against a labeled dataset, scores results with automated evaluators, and publishes experiments to `Langfuse` for comparison across prompt versions and models.

Together, these elements show how to **combine pipeline orchestration, agentic reasoning, evaluation, and observability** in a modular, maintainable, and reproducible workflow.

## 🤖 Agentic Workflow Design

### **Intent Detection Agent**
- A **LangGraph stateful agent**.  
- Produces an **intent label** and a **reason summary**.  
- Handles ambiguous queries via clarification loops.  

### **Response Generation Agent**
- Uses context from:  
  - `lookup_docs` – Retrieve KB answers.  
  - `get_user_claims` – Fetch user claim history.  
  - `create_claim` – Create a new claim in the DB.  
- Orchestrated by LangGraph with **conditional routing**.  
- Produces structured `ResponseOutput` with:  
  - Final message for the user  
  - Claim creation flag  
  - Escalation flag

<img src="kedro-agentic-workflows.png" alt="Use case diagram" width="800" height="700">

## 📂 Project Structure

```bash
kedro_agentic_workflows/
  ├── create_db_and_data.py                    # Script to create SQLite DB and seed with demo data
  ├── conf
  │   ├── base
  │   │   ├── catalog.yml                      # DB + shared datasets
  │   │   ├── catalog_genai_config.yml         # Provider-agnostic catalog (llm, tool_prompt, response_prompt)
  │   │   ├── credentials.yml.template         # Template for API + DB credentials (copy to credentials.yml)
  │   │   └── parameters.yml                   # Kedro pipeline parameters
  │   ├── langfuse                             # --env langfuse: provider-specific bindings + eval catalog
  │   │   ├── catalog_genai_config.yml         # intent_prompt, intent_tracer, autogen_tracer (Langfuse)
  │   │   └── catalog_evaluation.yml           # Evaluation pipeline catalog (Langfuse-only for now)
  │   ├── opik                                 # --env opik: same provider-specific names bound to Opik
  │   │   └── catalog_genai_config.yml         # intent_prompt, intent_tracer, autogen_tracer (Opik)
  │   └── local                                # gitignored; loaded only when --env local is passed explicitly
  ├── data
  │   ├── intent_detection
  │   │   ├── prompts                          # Intent detection prompts
  │   │   └── evaluation                       # Evaluation dataset and judge prompt
  │   └── response_generation
  │       └── prompts                          # Response generation prompts
  └── src
      └── kedro_agentic_workflows
          ├── datasets
          │   ├── sqlalchemy_dataset.py        # Custom Kedro dataset for SQLAlchemy engines
          │   └── langfuse_evaluation_dataset.py  # Kedro dataset bridging local files ↔ Langfuse datasets
          ├── pipelines
          │   ├── intent_detection                     # Provider-agnostic; uses generic dataset names
          │   │   ├── agent.py                         # IntentDetectionAgent (LangGraph)
          │   │   ├── nodes.py                         # Kedro nodes (session, context, intent)
          │   │   └── pipeline.py                      # Kedro pipeline
          │   ├── response_generation                  # LangGraph response variant (default)
          │   │   ├── agent.py                         # ResponseGenerationAgent
          │   │   ├── tools.py                         # Tool definitions (lookup_docs, claims, …)
          │   │   ├── nodes.py                         # Kedro nodes
          │   │   └── pipeline.py                      # Kedro pipeline
          │   ├── response_generation_autogen          # AutoGen variant, traced via autogen_tracer
          │   │   ├── agent.py                         # AutoGen AssistantAgent + structured output
          │   │   ├── tools.py                         # Tool definitions
          │   │   ├── nodes.py                         # Kedro nodes (wraps invocation in OTel span)
          │   │   └── pipeline.py                      # Kedro pipeline
          │   ├── response_generation_openai           # OpenAI Agents SDK variant (untraced)
          │   │   ├── agent.py                         # agents.Agent + Runner.run_sync
          │   │   ├── tools.py                         # @function_tool definitions
          │   │   ├── nodes.py                         # Kedro nodes
          │   │   └── pipeline.py                      # Kedro pipeline
          │   └── intent_detection_evaluation          # Langfuse-only; reorg coming in a follow-up PR
          │       ├── nodes.py                         # Kedro nodes (run experiment, score, log)
          │       └── pipeline.py                      # Kedro pipeline
          ├── utils.py                         # Shared utilities: KedroAgent, message logging
          └── settings.py                      # Global project settings
```

### Provider switching at a glance

Pipelines reference **generic** dataset names — `intent_prompt`, `intent_tracer`, `autogen_tracer`, `tool_prompt`, `response_prompt`, `llm`, `llm_openai`, `llm_autogen`. Each Kedro config env (`conf/langfuse/`, `conf/opik/`) binds those same names to provider-specific dataset classes from `kedro_datasets_experimental`. Switching providers is a CLI flag — no code or catalog edit needed:

```bash
kedro run --env langfuse --params user_id=3   # default; --env can be omitted
kedro run --env opik     --params user_id=3
```

## 🧾 Prompt Management

This project separates prompt templates by agent type and manages them with Kedro datasets.

- **Intent Detection** → JSON prompts tracked via the experimental `PromptDataset` from either the `langfuse` or `opik` provider package — selected by the active `--env`.
- **Response Generation** → Static `.txt` and `.yml` prompts managed via the experimental `langchain.PromptDataset`.

### Intent Detection Prompts

Stored under: `data/intent_detection/prompts`

Purpose: Classify user queries into categories (general_question, claim_new, existing_claim_question, clarification) and optionally request clarification when input is ambiguous.

We use experimental Kedro datasets for observability and prompt management:

- `intent_prompt_langfuse.json` stored using [`langfuse.PromptDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/langfuse.PromptDataset/) that integrates with [Langfuse](https://langfuse.com/).
- `intent_prompt_opik.json` stored using [`opik.PromptDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/opik.PromptDataset/) that integrates with [Opik](https://www.comet.com/opik).

Both datasets wrap the respective observability platform's API and allow us to manage prompts, track changes, and enable tracing/evaluation.

Pipelines always reference the **generic** name `intent_prompt`. Each provider env binds it to its own dataset class:

```yaml
# conf/langfuse/catalog_genai_config.yml
intent_prompt:
  type: kedro_datasets_experimental.langfuse.PromptDataset
  filepath: data/intent_detection/prompts/intent_prompt_langfuse.json
  prompt_name: "intent-classifier"
  prompt_type: "chat"
  credentials: langfuse_credentials
  sync_policy: local        # local|remote|strict
  mode: sdk                 # sdk keeps Langfuse-side prompt-version tracking
  load_args:
    version: ${runtime_params:intent_prompt_version, 1}
```

```yaml
# conf/opik/catalog_genai_config.yml
intent_prompt:
  type: kedro_datasets_experimental.opik.PromptDataset
  filepath: data/intent_detection/prompts/intent_prompt_opik.json
  prompt_name: "intent-classifier"
  prompt_type: "chat"
  credentials: opik_credentials
  sync_policy: local
  mode: langchain           # Opik sdk mode doesn't yet support version loading
```

The intent agent duck-types the returned prompt — if it exposes `get_langchain_prompt()` (Langfuse SDK mode) it's converted to a LangChain template; otherwise it's used as-is (mode `langchain`). No provider-specific imports.

### Response Generation Prompts

Stored under: `data/response_generation/prompts`

Purpose: Generate personalized responses that combine user context, user claims data and knowledge base content and decide which tools to call to retrieve this content.

Unlike intent detection, these are static templates managed via Kedro's experimental [`langchain.PromptDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/langchain.PromptDataset/):

- `tool.txt` – instruction for tool usage (defines how the LLM should decide when and how to call tools).
- `response.yml` – instruction for response style, tone, and overall reasoning with user-level template, receiving context (intent, claim data, docs) and instructing the model on what to answer.

Example catalog entries (shared across providers, so they live once in `conf/base/catalog_genai_config.yml`):

```yaml
tool_prompt:
  type: kedro_datasets_experimental.langchain.PromptDataset
  filepath: data/response_generation/prompts/tool.txt
  template: PromptTemplate
  dataset:
    type: text.TextDataset

response_prompt:
  type: kedro_datasets_experimental.langchain.PromptDataset
  filepath: data/response_generation/prompts/response.yml
  template: ChatPromptTemplate
  dataset:
    type: yaml.YAMLDataset
```

## ✏️ Tracing

The project supports tracing with either `Langfuse` or `Opik`, selected by the active Kedro env (`--env langfuse` is the default; pass `--env opik` to switch). Pipelines reference two generic tracer names:

- `intent_tracer` — a LangChain callback used by the intent flow (mode `langchain`).
- `autogen_tracer` — an OpenTelemetry `Tracer` used by the AutoGen response variant (mode `autogen`). The AutoGen node wraps execution in `tracer.start_as_current_span("response_generation")`, which is identical across both providers.

Each env binds those names to the appropriate dataset class:

```yaml
# conf/langfuse/catalog_genai_config.yml
intent_tracer:
  type: kedro_datasets_experimental.langfuse.TraceDataset
  credentials: langfuse_credentials
  mode: langchain

autogen_tracer:
  type: kedro_datasets_experimental.langfuse.TraceDataset
  credentials: langfuse_credentials
  mode: autogen
```

```yaml
# conf/opik/catalog_genai_config.yml
intent_tracer:
  type: kedro_datasets_experimental.opik.TraceDataset
  credentials: opik_credentials
  mode: langchain

autogen_tracer:
  type: kedro_datasets_experimental.opik.TraceDataset
  credentials: opik_credentials
  mode: autogen
```

> **Note:** the Opik snippet above shows the target state. The actual [`conf/opik/catalog_genai_config.yml`](conf/opik/catalog_genai_config.yml) currently carries two `TEMP` workarounds for upstream kedro-datasets bugs — `autogen_tracer` points at a separate `opik_credentials_autogen` block (isolating the OTLP `endpoint`), and `intent_tracer` carries an explicit `project_name:` override.

AutoGen mode requires the OTLP endpoint URL in credentials (e.g. `https://cloud.langfuse.com/api/public/otel/v1/traces`; the Opik equivalent is `https://www.comet.com/opik/api/v1/private/otel/v1/traces`). See [docs for `langfuse.TraceDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/langfuse.TraceDataset/) and [`opik.TraceDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/opik.TraceDataset/) for the full mode/credentials matrix.

> The `response_generation_openai` pipeline (OpenAI Agents SDK variant) is currently not wired to either tracer.

## 🧪 Evaluation

> **Scope note (this PR):** the evaluation pipeline below currently runs on **Langfuse only** and uses provider-named entries in `conf/langfuse/catalog_evaluation.yml`. The catalog only loads under the default `--env langfuse` — passing `--env opik` will omit it, and `kedro run --pipelines intent_detection_evaluation --env opik` will fail because the eval datasets won't resolve. Reorganising it to follow the same provider-agnostic shape as the main project (generic dataset names, swap via `--env`) is tracked as a follow-up PR. Class names have been updated to the 9.4.0 names so the catalog keeps loading after the bump, but the eval pipeline itself is untouched in this change.

The project includes an **intent detection evaluation pipeline** that runs the intent classification agent against a labeled dataset and scores results using two evaluators. It integrates with [Langfuse](https://langfuse.com/) so results, traces, and scores are visible in the Langfuse UI.

### How it works

The pipeline:
1. Loads the **evaluation dataset** (labeled question/intent pairs) from a local JSON file and syncs it to Langfuse.
2. Runs the **Intent Detection Agent** on each item, recording traces as Langfuse observations linked to the prompt and model.
3. Scores each result with two evaluators:
   - **Intent accuracy** — binary match between predicted and expected intent.
   - **Reason quality** — LLM-as-a-judge score (1–5) evaluating the reasoning behind the prediction.
4. Publishes the experiment to Langfuse with all scores, traces, and metadata.

### `langfuse.EvaluationDataset`

The evaluation dataset is managed by the experimental `langfuse.EvaluationDataset`, a Kedro dataset that bridges a local JSON/YAML file with a remote Langfuse dataset. It supports two sync policies:

- **`local`** — the local file is the source of truth; `load()` upserts all local items to remote (creating new items or updating existing ones matched by `id`). `save()` upserts to remote and merges back into the local file (new data takes precedence).
- **`remote`** — the remote Langfuse dataset is the source of truth. `load()` fetches remote as-is; `save()` upserts items to remote without writing to any local file. Supports versioned snapshots via the `version` parameter (`langfuse>=3.14.0`).

Lifecycle operations (update, archive, delete) are delegated to the native Langfuse API — the dataset handles load/save only.

> **Note:** this class is now published upstream as
> `kedro_datasets_experimental.langfuse.EvaluationDataset` (kedro-datasets 9.4.0),
> and the catalog entry below uses the upstream class. A stale local copy at
> `src/kedro_agentic_workflows/datasets/langfuse_evaluation_dataset.py` predates
> the upstream release and will be deleted in the eval reorg follow-up PR.

Catalog entry (`conf/langfuse/catalog_evaluation.yml`):

```yaml
intent_evaluation_data:
  type: kedro_datasets_experimental.langfuse.EvaluationDataset
  dataset_name: evaluations/intent_agent_evaluation
  filepath: data/intent_detection/evaluation/intent_evaluation.json
  sync_policy: local
  credentials: langfuse_credentials
  metadata:
    created_by: kedro
```

### Running the evaluation pipeline

```bash
kedro run --pipelines intent_detection_evaluation --params intent_prompt_version=1,model_name=gpt-4o
```

The `intent_prompt_version` and `model_name` parameters are used to name the experiment in Langfuse (e.g., `intent_prompt_v1_model_gpt-4o`), making it easy to compare runs across prompt iterations and models.

### Evaluation data

Stored at `data/intent_detection/evaluation/intent_evaluation.json` — a JSON array of labeled items:

```json
{
  "id": "intent_001",
  "input": { "question": "How do I submit a claim for a car accident?" },
  "expected_output": { "intent": "general_question", "reason": "User is asking about the process." }
}
```

Each item requires `input` (with a `question` field) and `expected_output` (with `intent` and `reason` fields). Items with an `id` are upserted on sync (created or updated); items without `id` create new entries every time.

## ⚙️ Project Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/kedro-agentic-workflows.git
cd kedro-agentic-workflows
```

### 2. Install Requirements
```bash
pip install -r requirements.txt
```

### 3. Set Up API Credentials

Copy [`conf/base/credentials.yml.template`](conf/base/credentials.yml.template) to `conf/base/credentials.yml` and fill in real values. The `conf/**/*credentials*` pattern in `.gitignore` keeps secrets out of git (with a single negation exception for the `.template` file). Include `endpoint` for both providers if you plan to run the AutoGen pipeline (autogen mode uses OTLP).

Why `conf/base/` and not `conf/local/`? Because `default_run_env = "langfuse"` (in `settings.py`) means a plain `kedro run` loads `conf/base/` + `conf/langfuse/` — `conf/local/` is not in the default stack. The Kedro CLI's `--env` flag takes a single env name (no layering), so credentials need to live somewhere that's loaded by default. `conf/base/credentials.yml` is the simplest place.

## ▶️ Running the Project

### 1. Create Database and Seed Data
```bash
python create_db_and_data.py
```

This creates:
* A SQLite DB with `user`, `session`, `claim` and `message` and `doc` tables.
* Example users (IDs 1, 2, 3) with claims.
* A knowledge base with Q&A docs - `doc` table.

### 2. Run Kedro Pipeline

The project ships three response variants on top of the shared intent-detection pipeline. Pick the one you want with `--pipelines` and the provider with `--env`. `--env` defaults to `langfuse`.

> **Heads-up:** `default_run_env = "langfuse"` (see `src/kedro_agentic_workflows/settings.py`) means a plain `kedro run` loads `conf/base/` + `conf/langfuse/`, **not** `conf/local/`. Put your real credentials in `conf/base/credentials.yml` (gitignored — see [Set Up API Credentials](#3-set-up-api-credentials) below). `--env` accepts a single env name, so you can't layer `conf/local/` on top via the CLI; if you must keep credentials in `conf/local/`, you'd need to revert `default_run_env` and rewire the catalog.

| Scenario | Command |
|---|---|
| Default (LangGraph response), Langfuse tracing | `kedro run --params user_id=3` |
| Default (LangGraph response), Opik tracing | `kedro run --env opik --params user_id=3` |
| AutoGen response, Langfuse tracing (OTel spans) | `kedro run --pipelines autogen --params user_id=3` |
| AutoGen response, Opik tracing (OTel spans) | `kedro run --pipelines autogen --env opik --params user_id=3` |
| OpenAI Agents SDK response (untraced) | `kedro run --pipelines openai --params user_id=3` |

Pipeline execution flow:

* Intent Detection Pipeline — classify query.
* Response Generation Pipeline — decide tool usage and generate response.

### 3. Run Evaluation Pipeline

Run the intent detection agent against a labeled evaluation dataset:
```bash
kedro run --pipelines intent_detection_evaluation --params intent_prompt_version=1,model_name=gpt-4o
```

Results are published as a Langfuse experiment. The eval pipeline is currently Langfuse-only — see the [Evaluation](#-evaluation) section.

## 💬 Conversation Example

```bash
Hi Charlie! 👋 How can I help you today? You can ask me a question, open a new claim, or follow up on the existing one.

================================ Human Message =================================
show me all my claims

================================== Ai Message ==================================
Intent classified: existing_claim_question
Reason: The user is asking to see all their claims, which implies they are inquiring about existing claims.

================================== Ai Message ==================================
Tool Calls: get_user_claims (call_6hZXCx7QZBDx0qPCSosDiZYO) Call ID: call_6hZXCx7QZBDx0qPCSosDiZYO Args: user_id: 3 

================================= Tool Message =================================
Name: get_user_claims [{"id": 1, "title": "Car Accident Claim", "status": "Pending", "problem": "User was involved in a minor car accident and submitted documents.", "solution": null, "created_at": "2025-09-04 14:11:49"}, {"id": 2, "title": "Laptop Damage Claim", "status": "Resolved", "problem": "Laptop stopped working after water damage.", "solution": "Claim approved. User received reimbursement of $800.", "created_at": "2025-09-04 14:11:49"}]

================================== Ai Message ==================================
Thank you for reaching out.

Based on the information we found regarding your issue: You have two claims. The "Car Accident Claim" is currently pending, and the "Laptop Damage Claim" has been resolved with a reimbursement of $800.

If you have any further questions, feel free to ask.
```