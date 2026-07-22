# Healthcare GraphRAG with Kedro

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

A complete GraphRAG demo built with Kedro. Takes 55,500 synthetic patient records, builds a knowledge graph, indexes it into a vector database, and exposes an agentic Q&A interface — all handled as modular Kedro pipelines.

<img width="1052" height="750" alt="image" src="https://github.com/user-attachments/assets/a7182819-f254-44d4-a5cb-bf6c0137dbab" />


---

## What it demonstrates

- **Kedro as a GenAI pipeline authoring tool** — five modular pipelines take raw data all the way to an AI agent, with every intermediate dataset tracked in the catalog
- **GraphRAG pattern** — semantic search is automatically enriched with connected entities from the knowledge graph before being passed to the LLM, giving the agent structural context that pure vector search misses
- **Multi-backend storage** — knowledge graph (NetworkX JSON), entity statistics (SQLite), and vector embeddings (ChromaDB) all written from the same pipeline run with unified catalog management
- **Ontology update pattern** — the `graph_update` pipeline demonstrates incremental graph evolution, merging new records into an existing ontology without rebuilding from scratch
- **`LLMContextNode`** — Kedro's experimental node type assembles the LLM, prompt template, and graph-aware tools into a typed `LLMContext` before the agent runs
- **`networkx.JSONDataset`** — the knowledge graph is persisted using Kedro's built-in NetworkX dataset, keeping graph structure and edge attributes in a human-readable JSON format
- **Agentic pipeline** — the `query_answering` pipeline runs an OpenAI function-calling agent that decides which tools to call and how many times
- **Kedro-Viz** — live pipeline DAG explorer shows the full data lineage from CSV to agent report

---

## Architecture

```
healthcare_dataset.csv (55,500 rows)
        │
        ▼  data_ingestion
        ├── cleaned_healthcare_data
        ├── entity_summaries
        └── entity_statistics → SQLite (relational store)

        cleaned_healthcare_data + entity_summaries
        │
        ▼  graph_construction
        ├── knowledge_graph (NetworkX JSON, 30 nodes / 120 edges)
        └── knowledge_graph.html (D3.js visualisation)

        existing_knowledge_graph + cleaned_healthcare_data (5,000 most recent)
        │
        ▼  graph_update  (run explicitly — not part of kedro run)
        └── knowledge_graph (updated in-place) + refreshed HTML

        entity_summaries + knowledge_graph
        │
        ▼  vector_indexing
        └── chroma_collection (18 docs, OpenAI embeddings)

        knowledge_graph + chroma_collection + agent_prompt
        │
        ▼  query_answering
        └── agent_report.json
```

### Five Kedro pipelines

| Pipeline | What it does |
|---|---|
| `data_ingestion` | Cleans the CSV, computes per-entity statistics, persists to SQLite |
| `graph_construction` | Builds a NetworkX graph of entity relationships, renders interactive D3.js HTML |
| `graph_update` | Incremental ontology update: merges recent records into the existing graph (run explicitly) |
| `vector_indexing` | Generates 18 entity summary documents, embeds them with OpenAI, stores in ChromaDB |
| `query_answering` | Runs an OpenAI function-calling agent over a configurable list of sample questions |

### Knowledge graph

30 nodes across 6 entity types, 120 edges. Edge weight = patient count.

| Entity type | Count | Relationships |
|---|---|---|
| Medical Condition | 6 | `TREATED_WITH`, `COVERED_BY`, `ADMITTED_AS`, `SHOWS_RESULT`, `ASSOCIATED_WITH` |
| Medication | 5 | — |
| Insurance Provider | 5 | — |
| Admission Type | 3 | — |
| Test Result | 3 | — |
| Blood Type | 8 | — |

### Agent tools

The `query_answering` agent has two tools:

- **`search_knowledge_base`** — semantic search over ChromaDB, automatically enriched with connected entities from the knowledge graph (the GraphRAG step)
- **`get_graph_context`** — targeted neighbour lookup for a named entity

---

## Setup

### Prerequisites

- Python 3.10+
- An OpenAI API key (required for `vector_indexing` and `query_answering`; the graph and SQLite pipelines work without it)

### Install

```bash
pip install -r requirements.txt
pip install -e src/
```

### Configure credentials

Add your OpenAI API key to `conf/local/credentials.yml` (gitignored):

```yaml
openai:
  api_key: "sk-..."

sqlite_db:
  con: "sqlite:///data/07_model_output/healthcare_stats.db"
```

### First run

The easiest way to get started is via the Streamlit app:

```bash
streamlit run app/streamlit_app.py
```

In **The Story** tab, click **▶ Run Graph Pipeline**. This runs `data_ingestion` and `graph_construction`, populating the SQLite store and building the knowledge graph (~3s, no API key needed). Click **▶ Rebuild Vector Index** to run the full pipeline including embeddings and the agent (requires OpenAI key).

---

## Running the pipelines

```bash
# Full pipeline (requires OpenAI API key)
kedro run

# Graph + SQLite only — fast (~3s), no API key needed
kedro run --pipelines data_ingestion,graph_construction

# Incremental ontology update — merges 5,000 most recent records into existing graph
kedro run --pipelines graph_update

# Vector index only — re-embeds documents (costs API tokens)
kedro run --pipelines vector_indexing

# Agent report only — runs the agent over the sample questions in parameters_query_answering.yml
kedro run --pipelines query_answering
```

To customise the sample questions the agent answers, edit `conf/base/parameters_query_answering.yml`.

---

## Streamlit app

```bash
streamlit run app/streamlit_app.py
```

The app reads credentials from `conf/local/credentials.yml` via Kedro's config system — no environment variables needed.

The app has three tabs:

- **The Story** — a narrative walkthrough of the pipeline with inline run buttons, an interactive D3.js knowledge graph (30 nodes, drag/zoom/hover), and the SQLite entity statistics table. Run buttons are embedded in the narrative: **▶ Run Graph Pipeline** (`data_ingestion` + `graph_construction`, ~3s, no API key), **▶ Update Graph** (`graph_update`), and **▶ Rebuild Vector Index** (full pipeline, requires API key).
- **Ask the Graph** — ask a question and see plain RAG and GraphRAG answer side by side. Expanders under each answer show exactly what context the model received, making the difference between the two approaches concrete.
- **Pipeline** — an embedded Kedro-Viz DAG explorer showing the full data lineage from raw CSV to agent report, plus a card for each sub-pipeline explaining what it does and what it produces.

---

## Project structure

```
├── app/
│   └── streamlit_app.py          # Streamlit dashboard
├── conf/
│   ├── base/
│   │   ├── catalog.yml           # Dataset definitions
│   │   ├── credentials.yml       # SQLite connection (non-sensitive)
│   │   ├── parameters_*.yml      # Per-pipeline parameters
│   │   └── parameters_query_answering.yml  # Sample questions, ChromaDB config
│   └── local/
│       └── credentials.yml       # OpenAI key (gitignored)
├── data/
│   ├── 01_raw/                   # healthcare_dataset.csv
│   ├── 04_feature/               # knowledge_graph.json
│   ├── 06_models/chroma_db/      # ChromaDB persistent storage
│   ├── 07_model_output/          # graph_metadata.csv, healthcare_stats.db (SQLite)
│   ├── 08_reporting/             # knowledge_graph.html, agent_report.json
│   └── prompts/                  # healthcare_agent.json (LangChainPromptDataset)
└── src/graphrag/pipelines/
    ├── data_ingestion/
    ├── graph_construction/
    ├── graph_update/
    ├── vector_indexing/
    └── query_answering/
```

---

## Data

The dataset is a synthetic healthcare CSV with 55,500 rows and 15 columns (age, gender, blood type, condition, medication, insurer, admission type, test result, billing amount, etc.). Doctor and hospital columns are excluded from the graph — they have ~40,000 unique synthetic values with no meaningful structure.

Source: [Kaggle — Healthcare Dataset](https://www.kaggle.com/datasets/prasad22/healthcare-dataset)
