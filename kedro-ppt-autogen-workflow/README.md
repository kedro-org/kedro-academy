# PPT AutoGen Workflow

Automated PowerPoint presentation generation from structured YAML instructions using AutoGen agents and data-driven utilities.

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

## Table of Contents

- [Architecture](#architecture)
- [Data Flow](#data-flow)
- [Pipeline Structure](#pipeline-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Architecture

### Overview

This project implements two pipeline patterns for generating PowerPoint presentations:

1. **Multi-Agent (MA) Pipeline** - Uses specialized agents (Planner, Chart Generator, Summarizer, Critic) working in collaboration
2. **Single-Agent (SA) Pipeline** - Uses one agent with all necessary tools

Both pipelines follow a **three-phase architecture**:
- **Preprocessing** (Deterministic): Parse YAML instructions into structured configurations
- **Agentic** (LLM-powered): Agents analyze data on demand and generate content
- **Postprocessing** (Deterministic): Assemble final presentations from generated content

### Key Design Principles

1. **Separation of Concerns**: Clear boundaries between deterministic and agentic logic
2. **On-Demand Analysis**: Agents analyze data based on instructions, not pre-computed metrics
3. **Code Reuse**: Shared preprocessing and postprocessing functions in `base/` module
4. **Tool-Based Data Access**: Agents access raw data through tools, enabling flexible analysis
5. **Self-Contained Pipelines**: Each pipeline (MA/SA) includes all necessary steps
6. **Base Module Independence**: Base module is self-sufficient with no dependencies on pipelines

## Data Flow

### Multi-Agent Pipeline Flow

```
Input Files
├── slide_generation_requirements.yaml
└── sales_50_products.csv
    │
    ▼
[PREPROCESSING - Deterministic]
    │
    ├─ parse_ma_slide_requirements (in MA pipeline)
    │  └─→ ma_slide_configs (structured configs for each slide)
    │
    ▼
[AGENTIC - LLM-powered]
    │
    ├─ llm_context_node (Planner) → planner_context
    ├─ llm_context_node (Chart Generator) → chart_context
    ├─ llm_context_node (Summarizer) → summarizer_context
    ├─ llm_context_node (Critic) → critic_context
    │
    └─ orchestrate_multi_agent_workflow
       ├─ Planner analyzes requirements using analyze_data tool
       ├─ Chart Generator creates charts using generate_chart tool
       ├─ Summarizer generates summaries using generate_summary tool
       └─ Critic reviews quality using QA tools
       │
       └─→ ma_slide_content (charts + summaries per slide)
    │
    ▼
[POSTPROCESSING - Deterministic]
    │
    └─ assemble_presentation (from base module)
       └─→ sales_analysis_ma.pptx
```

### Single-Agent Pipeline Flow

```
Input Files
├── slide_generation_requirements.yaml
└── sales_50_products.csv
    │
    ▼
[PREPROCESSING - Deterministic]
    │
    ├─ parse_sa_slide_requirements (in SA pipeline)
    │  └─→ sa_slide_configs (structured configs for each slide)
    │
    ▼
[AGENTIC - LLM-powered]
    │
    ├─ llm_context_node (PPT Generator) → ppt_llm_context
    │
    └─ run_ppt_agent
       ├─ Agent analyzes data using analyze_data tool
       ├─ Agent creates charts using generate_chart tool
       └─ Agent generates summaries using generate_summary tool
       │
       └─→ sa_slide_content (charts + summaries per slide)
    │
    ▼
[POSTPROCESSING - Deterministic]
    │
    └─ assemble_presentation (from base module)
       └─→ sales_analysis_sa.pptx
```

### How Agents Analyze Data

**Key Point**: Agents analyze data **on demand** based on instructions, not from pre-computed metrics.

1. **Tools receive raw data**: Tool builder functions receive the full `sales_data` DataFrame
2. **Agents query dynamically**: Agents use natural language queries to request specific analyses
3. **Tools perform analysis**: Tools filter, aggregate, and compute metrics based on agent queries
4. **Results returned**: Tools return JSON results that agents use to generate charts/summaries

Example:
- Agent receives instruction: "Show top 10 products by sales"
- Agent calls `analyze_data("Get top 10 products by FY_Sales, sorted descending")`
- Tool filters data, sorts, and returns top 10 as JSON
- Agent uses results to generate chart

## Pipeline Structure

### Architecture Overview

The project uses **self-contained pipelines** where each pipeline (MA/SA) includes all necessary steps:

1. **Preprocessing nodes** (in each pipeline): Parse YAML instructions into structured configs
   - MA pipeline: `parse_ma_slide_requirements` → `ma_slide_configs`
   - SA pipeline: `parse_sa_slide_requirements` → `sa_slide_configs`
   - Both use shared functions from `base.preprocessing` module

2. **Agentic nodes** (pipeline-specific): LLM-powered content generation
   - MA pipeline: 4 `llm_context_node`s + 1 orchestration node → `ma_slide_content`
   - SA pipeline: 1 `llm_context_node` + 1 agent execution node → `sa_slide_content`

3. **Postprocessing nodes** (in each pipeline): Assemble final presentations
   - Both pipelines: `assemble_presentation` → `sales_analysis_ma` or `sales_analysis_sa`
   - Uses shared function from `base.postprocessing` module

### Code Organization

**Base Module** (`src/ppt_autogen_workflow/base/`):
- **`preprocessing.py`**: Shared parsing functions (`parse_instructions_yaml`, `parse_slide_requirements`)
- **`postprocessing.py`**: Shared presentation assembly (`assemble_presentation`, `create_slide`, `combine_presentations`)
- **`tools.py`**: Shared tool builders for agents (data analysis, chart generation, summaries)
- **`agent.py`**: Base agent classes
- **`utils.py`**: Shared utilities

**Pipeline Modules** (`src/ppt_autogen_workflow/pipelines/`):
- **`ma_slide_generation_autogen/`**: Complete MA pipeline with preprocessing, agentic, and postprocessing nodes
- **`sa_slide_generation_autogen/`**: Complete SA pipeline with preprocessing, agentic, and postprocessing nodes

### Available Pipelines

**Full pipelines** (self-contained, ready for production):
```bash
kedro run --pipeline=ma_slide_generation_autogen
kedro run --pipeline=sa_slide_generation_autogen
kedro run  # Runs default (MA pipeline)
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- OpenAI API key (or compatible API)

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd kedro-ppt-autogen-workflow

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

#### 3.1. Set Up Credentials

Create `conf/local/credentials.yml`:

```yaml
openai:
  api_key: "${oc.env:OPENAI_API_KEY}"
  base_url: "${oc.env:OPENAI_API_BASE}"
```

#### 3.2. Export Environment Variables

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="your-base-url"  # Optional, defaults to OpenAI
```

#### 3.3. Prepare Input Data

1. **Sales Data**: Place your CSV file at `data/ppt_generation/sample/sales_50_products.csv`
2. **Slide Requirements**: Edit `data/ppt_generation/sample/slide_generation_requirements.yaml`

Example requirements file:

```yaml
iterative_slide_generation:
  slide_1:
    objective:
      slide_title: "Top 10 Products Performance Analysis"
      chart_instruction: >
        Please generate a horizontal bar chart showing FY_Sales for the top 10 products
        by FY_Sales. Sort bars in descending order. Use the primary brand color #1F4E79.
      summary_instruction: >
        Please generate 3–5 concise bullet points summarizing the performance of the
        top 10 products by FY_Sales. Mention the overall total FY sales of these top
        10 products, highlight the top 1–2 products by name.
  slide_2:
    objective:
      slide_title: "Product Category Distribution"
      chart_instruction: >
        Create a pie chart showing the distribution of FY_Sales by Product_Category.
      summary_instruction: >
        Provide a brief analysis of the category distribution including the dominant
        categories and their contribution percentages.
```

### 4. Run Pipeline

**Multi-Agent Pipeline** (recommended for production):
```bash
kedro run --pipeline=ma_slide_generation_autogen
```

**Single-Agent Pipeline** (faster, simpler):
```bash
kedro run --pipeline=sa_slide_generation_autogen
```

**Default** (runs multi-agent):
```bash
kedro run
```

### 5. Check Outputs

- **MA Pipeline Output**: `data/ppt_generation/output/ma/sales_analysis.pptx`
- **SA Pipeline Output**: `data/ppt_generation/output/sa/sales_analysis.pptx`
- **Intermediate Content**: `data/ppt_generation/intermediate/ma/slide_content.json` (or `sa/`)

## Configuration

### Configuration Files

- **`conf/base/catalog.yml`**: Data catalog (input data, intermediate outputs, final outputs)
- **`conf/base/genai-config.yml`**: GenAI configuration (LLM client + all prompt datasets)
- **`conf/base/parameters.yml`**: Pipeline parameters (styling, layout, QA settings)

### Update LLM Model

Edit `conf/base/genai-config.yml`:

```yaml
llm_autogen:
  type: ppt_autogen_workflow.datasets.autogen_model_client.OpenAIChatCompletionClientDataset
  kwargs:
    model: "gpt-4o"  # or your preferred model
    temperature: 1
  credentials: openai
```

### Customize Styling and Layout

Edit `conf/base/parameters.yml`:

```yaml
styling:
  title_font: "Helvetica Neue"  # System font detected automatically
  title_size: 28
  text_size_small: 11
  title_color_rgb: [31, 78, 121]
  text_color_rgb: [51, 51, 51]

layout:
  content_left: 0.5
  content_top: 1.3
  chart_width: 5.0
  chart_height: 5.0
  summary_width: 4.0

quality_assurance:
  quality_standards: "Professional presentation standards with clear messaging"
  review_criteria: "Score 1-10, check chart/summary alignment, provide improvement recommendations"
```

### Modify Prompts

Edit prompt files in `data/ppt_generation/prompts/`:
- `ma/` - Multi-agent prompts (8 files: 4 system + 4 user prompts)
- `sa/` - Single-agent prompts (2 files: 1 system + 1 user prompt)

Prompts use placeholders that are filled during agent execution.

## Project Structure

```
├── conf/
│   ├── base/
│   │   ├── catalog.yml          # Dataset definitions
│   │   ├── parameters.yml       # Pipeline parameters
│   │   └── genai-config.yml     # LLM + prompt configuration
│   └── local/                    # Local credentials (gitignored)
│       └── credentials.yml
│
├── data/
│   └── ppt_generation/
│       ├── sample/               # Input data
│       │   ├── slide_generation_requirements.yaml
│       │   └── sales_50_products.csv
│       ├── prompts/              # Prompt templates
│       │   ├── ma/               # Multi-agent prompts (8 files)
│       │   └── sa/               # Single-agent prompts (2 files)
│       ├── intermediate/         # Intermediate outputs
│       │   ├── ma/
│       │   │   ├── slide_configs_parsed.json
│       │   │   └── slide_content.json
│       │   └── sa/
│       │       ├── slide_configs_parsed.json
│       │       └── slide_content.json
│       └── output/               # Final presentations
│           ├── ma/
│           │   └── sales_analysis.pptx
│           └── sa/
│               └── sales_analysis.pptx
│
└── src/ppt_autogen_workflow/
    ├── base/                     # Shared infrastructure (self-sufficient)
    │   ├── __init__.py           # Exports base classes and utilities
    │   ├── agent.py              # BaseAgent with structured output support
    │   ├── output_models.py      # Pydantic models (ChartOutput, SummaryOutput, etc.)
    │   ├── tools.py              # Shared tool builders (data analysis, chart, summary)
    │   ├── preprocessing.py      # Shared preprocessing functions (parse_instructions_yaml, parse_slide_requirements)
    │   ├── postprocessing.py     # Shared postprocessing functions (assemble_presentation, create_slide, combine_presentations)
    │   └── utils.py              # Shared utilities (format_prompt, SYSTEM_FONT)
    │
    ├── datasets/
    │   └── autogen_model_client.py  # LLM client dataset
    │
    ├── pipelines/
    │   ├── ma_slide_generation_autogen/  # Complete MA pipeline (self-contained)
    │   │   ├── agent.py          # PlannerAgent, ChartGeneratorAgent, SummarizerAgent, CriticAgent
    │   │   ├── nodes.py          # parse_ma_slide_requirements, orchestrate_multi_agent_workflow
    │   │   ├── pipeline.py       # Full pipeline: preprocessing + agentic + postprocessing
    │   │   └── utils.py          # format_ma_prompts (pipeline-specific)
    │   │
    │   └── sa_slide_generation_autogen/  # Complete SA pipeline (self-contained)
    │       ├── agent.py          # PPTGenerationAgent
    │       ├── nodes.py          # parse_sa_slide_requirements, run_ppt_agent
    │       ├── pipeline.py       # Full pipeline: preprocessing + agentic + postprocessing
    │       └── utils.py          # format_sa_prompts (pipeline-specific)
    │
    ├── pipeline_registry.py      # Registers full pipelines
    └── settings.py
```

## Troubleshooting

### Common Issues

**Error: "Environment variable 'OPENAI_API_KEY' not found"**
- Ensure `conf/local/credentials.yml` exists
- Export `OPENAI_API_KEY` in your terminal
- Check that credentials file uses correct environment variable names

**Error: "No 'iterative_slide_generation' found in YAML"**
- Verify `slide_generation_requirements.yaml` has correct structure
- Check YAML syntax (indentation, quotes)

**Empty or invalid presentations**
- Verify sales data CSV is loaded correctly
- Check agent logs for tool invocation errors
- Ensure chart/summary generation tools are working

**Agent not using tools**
- Check that tools are properly built with sales data
- Verify agent system prompts instruct tool usage
- Review agent response logs for tool invocation

**Pipeline execution errors**
- Ensure all required datasets exist (check catalog.yml)
- Verify pipeline dependencies are correct
- Check that base module functions are properly imported

## License

This project uses the Kedro framework. See [Kedro license](https://github.com/kedro-org/kedro/blob/main/LICENSE.md).
