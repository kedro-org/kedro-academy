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
* **Dataset-based evaluation** – Runs the agent against a labeled dataset, scores results with automated evaluators, and publishes experiments to `Langfuse` or `Opik` for comparison across prompt versions and models.

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
  │   │   └── catalog_evaluation.yml           # Evaluation pipeline catalog (Langfuse)
  │   ├── opik                                 # --env opik: same provider-specific names bound to Opik
  │   │   ├── catalog_genai_config.yml         # intent_prompt, intent_tracer, autogen_tracer (Opik)
  │   │   └── catalog_evaluation.yml           # Evaluation pipeline catalog (Opik)
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
          │   ├── autogen_model_client.py      # AutoGen OpenAIChatCompletionClient dataset
          │   └── openai_model_dataset.py      # OpenAI Agents SDK model dataset
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
          │   ├── intent_detection_evaluation          # Eval pipeline (Langfuse); run under default env
          │   │   ├── nodes.py                         # Evaluators + Langfuse run_experiment
          │   │   └── pipeline.py                      # Kedro pipeline
          │   └── intent_detection_evaluation_opik     # Eval pipeline (Opik); run with --env opik
          │       ├── nodes.py                         # Evaluators + opik.evaluation.evaluate
          │       └── pipeline.py                      # Kedro pipeline (mirrors the Langfuse one)
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

The project runs the intent classification agent against a labeled dataset and scores results with two evaluators. Like the rest of the project, the observability provider is a `--env` switch — there are two parallel pipelines, one per provider:

| Pipeline | Provider | Command |
|---|---|---|
| `intent_detection_evaluation` | Langfuse (default env) | `kedro run --pipelines intent_detection_evaluation --params intent_prompt_version=1,model_name=gpt-4o` |
| `intent_detection_evaluation_opik` | Opik (`--env opik`) | `kedro run --pipelines intent_detection_evaluation_opik --env opik --params intent_prompt_version=1,model_name=gpt-4o` |

Both use the same generic dataset names (`intent_evaluation_data`, `intent_judge_llm`, `intent_judge_prompt`, …), bound to provider-specific classes in `conf/langfuse/catalog_evaluation.yml` and `conf/opik/catalog_evaluation.yml`. Each pipeline must run under its matching env (the Opik pipeline needs `--env opik`).

> **Why two pipelines and not one `--env` switch?** Unlike tracing and prompts — where both providers expose the same LangChain/OTel interfaces — the experiment runners are structurally different: Langfuse uses `dataset.run_experiment(task=…, evaluators=[…])` returning `Evaluation`s, while Opik uses the free function `opik.evaluation.evaluate(dataset=…, task=…, scoring_functions=[…])` returning `ScoreResult`s, with different task/scorer signatures and tracing hooks. There's no shared interface to write one set of node functions against, so each provider gets its own pipeline. They're kept deliberately symmetric (same dataset names, node structure, and `intent_prompt_v{version}_model_{model}` experiment naming).

### How it works

Each pipeline:
1. Loads the **evaluation dataset** (labeled question/intent pairs) from a local JSON file and syncs it to the active provider (a Langfuse / Opik dataset).
2. Runs the **Intent Detection Agent** on each item, recording traces in that provider.
3. Scores each result with two evaluators:
   - **Intent accuracy** — binary match between predicted and expected intent.
   - **Reason quality** — LLM-as-a-judge score (1–5) evaluating the reasoning behind the prediction.
4. Publishes the experiment (named `intent_prompt_v{version}_model_{model}`) with all scores, traces, and metadata to the provider's UI.

### Evaluation datasets

The eval datasets are managed by the experimental `langfuse.EvaluationDataset` / `opik.EvaluationDataset` (both published in `kedro-datasets` 9.4.0), which bridge a local JSON/YAML file with a remote provider dataset via a `sync_policy` — `local` keeps the file as source of truth; `remote` treats the platform as source of truth. Lifecycle operations (update, delete) are delegated to each provider's native API.

Catalog entries (`conf/langfuse/catalog_evaluation.yml` and `conf/opik/catalog_evaluation.yml`):

```yaml
# conf/langfuse/catalog_evaluation.yml
intent_evaluation_data:
  type: kedro_datasets_experimental.langfuse.EvaluationDataset
  dataset_name: evaluations/intent_agent_evaluation
  filepath: data/intent_detection/evaluation/intent_evaluation.json
  sync_policy: local
  credentials: langfuse_credentials
```

```yaml
# conf/opik/catalog_evaluation.yml
intent_evaluation_data:
  type: kedro_datasets_experimental.opik.EvaluationDataset
  dataset_name: evaluations/intent_agent_evaluation
  filepath: data/intent_detection/evaluation/intent_evaluation.json
  sync_policy: local
  credentials: opik_credentials
```

The `intent_prompt_version` and `model_name` parameters name the experiment (e.g. `intent_prompt_v1_model_gpt-4o`) in both UIs, making runs comparable across prompt iterations and models. A standalone walkthrough of `opik.EvaluationDataset` sync behaviour lives in [`notebooks/e2e_opik_evaluation_dataset.ipynb`](notebooks/e2e_opik_evaluation_dataset.ipynb).

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

> **Note:** credentials go in `conf/base/` rather than the conventional `conf/local/`. With `default_run_env = "langfuse"`, a plain `kedro run` loads `conf/base/` + `conf/langfuse/` only — `conf/local/` is not loaded, and `--env` takes a single env name, so it can't be layered on top.

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

Credentials must be in `conf/base/credentials.yml` — see [Set Up API Credentials](#3-set-up-api-credentials).

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

Run the intent detection agent against a labeled evaluation dataset, with either provider:
```bash
# Langfuse (default env)
kedro run --pipelines intent_detection_evaluation --params intent_prompt_version=1,model_name=gpt-4o

# Opik
kedro run --pipelines intent_detection_evaluation_opik --env opik --params intent_prompt_version=1,model_name=gpt-4o
```

Results are published as an experiment in the active provider's UI — see the [Evaluation](#-evaluation) section.

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

## 🔀 Datasets vs Parameters for Prompts and LLMs

A common question is: *"Why use Kedro datasets for prompts and LLM configs when I could just put them in `parameters.yml`?"*

Both approaches work. Plain parameters require no extra setup and are already supported — you can put prompt text and model settings in `parameters.yml` today and access them via `params:` in your pipeline. The GenAI datasets in this project exist because they provide capabilities that parameters structurally cannot.

### The parameters approach (already works)

Nothing stops you from defining prompts and model config as parameters:

```yaml
# conf/base/parameters.yml
system_prompt: "You are a helpful insurance assistant. Classify the user's intent..."
model_name: "gpt-4o"
temperature: 0.0
```

Your node then receives raw values and must construct LLM clients and prompt objects manually:

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

def detect_intent(system_prompt: str, model_name: str, temperature: float, ...):
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ...])
    chain = prompt | llm
    ...
```

This is fine for quick prototyping and solo experiments.

### The datasets approach (what this project uses)

This project treats LLMs and prompts as catalog entries — typed datasets that return ready-to-use objects. For example, `conf/base/catalog_genai_config.yml` defines:

```yaml
llm:
  type: langchain.ChatOpenAIDataset
  kwargs:
    model: ${runtime_params:model_name, gpt-4o}
    temperature: 0.0
  credentials: openai

tool_prompt:
  type: kedro_datasets_experimental.langchain.PromptDataset
  filepath: data/response_generation/prompts/tool.txt
  template: PromptTemplate
  dataset:
    type: text.TextDataset
```

And `conf/langfuse/catalog_genai_config.yml` adds provider-specific prompt tracking:

```yaml
intent_prompt:
  type: kedro_datasets_experimental.langfuse.PromptDataset
  filepath: data/intent_detection/prompts/intent_prompt_langfuse.json
  prompt_name: "intent-classifier"
  prompt_type: "chat"
  credentials: langfuse_credentials
  sync_policy: local
  mode: sdk
  load_args:
    version: ${runtime_params:intent_prompt_version, 1}
```

These are wired into pipelines via [`llm_context_node`](src/kedro_agentic_workflows/pipelines/intent_detection/pipeline.py), which bundles the LLM and prompts into an [`LLMContext`](https://docs.kedro.org/en/stable/api/kedro.pipeline.LLMContext.html) object. The agent then accesses them as `self.context.llm` and `self.context.prompts["tool_prompt"]` — no manual construction needed.

### When to use which

| Concern | Parameters | Datasets |
|---|---|---|
| Setup effort | Minimal — add to `parameters.yml` | Catalog entry + prompt file (+ optional platform sync) |
| Runtime overrides | Native via `--params` | Via `${runtime_params:...}` resolver (e.g. `model_name`, `intent_prompt_version`) |
| What your node receives | Raw strings/dicts — you construct the LLM client and prompt objects yourself | Ready-to-use typed objects (`ChatOpenAI`, `PromptTemplate`, `ChatPromptTemplate`) via `LLMContext` |
| Credential handling | Risk of API keys leaking via `--params` (shell history, logs) | Isolated via `credentials:` — keys never appear in parameter space |
| Prompt versioning | Git only | Automatic — Kedro dataset versioning + platform-side tracking ([Langfuse](https://langfuse.com/), [Opik](https://www.comet.com/opik)) |
| Observability integration | None | Native — [`langfuse.PromptDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/langfuse.PromptDataset/) and [`opik.PromptDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/opik.PromptDataset/) sync prompts to the platform, linking them to traces and evaluations |
| Provider switching | Manual code changes to swap Langfuse ↔ Opik | `--env` flag, zero code changes (see [Provider switching at a glance](#provider-switching-at-a-glance)) |
| Evaluation workflows | Must build custom | Built-in with [`langfuse.EvaluationDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/langfuse.EvaluationDataset/) / [`opik.EvaluationDataset`](https://docs.kedro.org/projects/kedro-datasets/en/latest/api/kedro_datasets_experimental/opik.EvaluationDataset/) |

### Recommendation

Start with parameters if you are prototyping and want minimal setup. Move to datasets when you need versioned prompts, observability integration, credential isolation, or provider switching — which is typically when you move toward production or team collaboration.

Note that this project already uses both side by side: `user_id`, `docs_matches`, `intent_prompt_version`, and `model_name` live in [`parameters.yml`](conf/base/parameters.yml) as simple runtime values, while LLMs, prompts, and tracers are catalog datasets. The `${runtime_params:...}` resolver bridges the two — for example, `model_name` is a parameter that feeds into the `llm` dataset's `model` kwarg, and `intent_prompt_version` selects which prompt version to load from Langfuse/Opik.
