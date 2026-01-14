# PPT AutoGen Workflow

Automated PowerPoint presentation generation from structured YAML instructions using AutoGen agents and data-driven utilities.

[![Powered by Kedro](https://img.shields.io/badge/powered_by-kedro-ffc900?logo=kedro)](https://kedro.org)

## Table of Contents

- [Architecture](#architecture)
- [Pipeline Patterns](#pipeline-patterns)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Architecture

### Overview

This project implements two pipeline patterns for generating PowerPoint presentations:

1. **Multi-Agent (MA) Pipeline** - Uses specialized agents (Planner, Chart Generator, Summarizer, Critic) working in collaboration
2. **Single-Agent (SA) Pipeline** - Uses one agent with all necessary tools

Both pipelines follow the same architectural pattern:
- **Separation of Concerns**: Prompts are stored in YAML files, separate from code
- **Tool-Based Data Access**: Sales data is accessed through agent tools, not passed directly
- **Requirement-Driven**: Slide requirements are parsed and stored in agents during compilation
- **Agent Invocation**: Agents use their tools to generate charts and summaries

### Data Flow

```
Input Data (CSV) → Tools (with data access) → Agents → Generated Content → PPT Slides
```

### Key Components

1. **LLM Context Node** (`llm_context_node`): Kedro feature that bundles LLM + prompts + tools
   - Creates `LLMContext` objects containing model client, prompts dict, and tools dict
   - Reduces boilerplate by eliminating separate init_tools and compile nodes
   - Uses `tool()` helper to associate tool builder functions with Kedro datasets

2. **Shared Utilities** (`utils/`): Common implementations used by both pipelines
   - `tools_common.py`: Shared tool implementations (chart, summary, data lookup, slide creation)
   - `node_helpers.py`: Shared helper functions (format summary, extract results)
   - `chart_generator.py`, `summary_generator.py`, `ppt_builder.py`: Core generation logic

3. **Tools** (`tools.py`): Function tools that agents can invoke
   - Import shared implementations from `utils/tools_common.py`
   - MA pipeline: Each agent gets specific tools via separate tool builder functions
   - SA pipeline: Single agent gets all tools via `build_tools` function

4. **Agents** (separate agent files): AutoGen agents with specialized roles
   - MA pipeline: `agent_planner.py`, `agent_chart.py`, `agent_summarizer.py`, `agent_critic.py`
   - SA pipeline: `agent.py` with single PPTGenerationAgent
   - Base classes in `base/agent.py` with structured output support (Pydantic models)

5. **Nodes** (`nodes.py`): Kedro pipeline nodes
   - Import shared helpers from `utils/node_helpers.py` and pipeline-specific helpers
   - Use `LLMContext` to create agents with bundled LLM, prompts, and tools
   - `orchestrate_*/generate_*`: Coordinates agent execution

6. **Prompts** (`data/ppt_generation/prompts/`): YAML-based prompt templates
   - System prompts define agent behavior
   - User prompts define task instructions
   - Loaded as `LangChainPromptDataset` and accessed via `LLMContext.prompts`

## Pipeline Patterns

### Multi-Agent (MA) Pipeline

**Architecture**: Planner-driven with specialized agents using `llm_context_node`

```
1. create_planner_context    → Bundle LLM + prompts + tools for Planner
2. create_chart_context      → Bundle LLM + prompts + tools for ChartGenerator
3. create_summarizer_context → Bundle LLM + prompts + tools for Summarizer
4. create_critic_context     → Bundle LLM + prompts + tools for Critic
5. orchestrate_agents        → Create agents, coordinate execution
6. assemble_presentation     → Combine charts + summaries into slides
```

**Flow**:
- LLM contexts bundle model client, prompts, and tools for each agent
- Planner analyzes requirements and creates instructions
- Chart Generator creates charts using tools
- Summarizer creates summaries using tools (with chart status)
- Critic reviews slide content for quality
- All slides are combined into final presentation

**Features**:
- ✅ Quality assurance via Critic agent
- ✅ Specialized agents for each task
- ✅ Context passing between agents
- ✅ Intermediate outputs (charts, summaries) saved
- ✅ Clean separation via `llm_context_node` pattern

### Single-Agent (SA) Pipeline

**Architecture**: Single agent with all tools using `llm_context_node`

```
1. create_ppt_context      → Bundle LLM + prompts + tools for PPTGenerator
2. generate_presentation   → Create agent, generate charts and summaries
```

**Flow**:
- LLM context bundles model client, prompts, and tools
- Single agent receives queries to generate charts/summaries
- Agent uses its tools (generate_sales_chart, generate_business_summary)
- Results are extracted and combined into slides

**Features**:
- ✅ Simpler architecture (2 nodes)
- ✅ Faster execution
- ✅ Single agent handles all tasks
- ✅ Clean separation via `llm_context_node` pattern
- ❌ No quality assurance step

## Quick Start

### 1. Prerequisites

- Python 3.11+
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
- **Charts** (MA only): `data/ppt_generation/intermediate/ma/charts/`
- **Summaries** (MA only): `data/ppt_generation/intermediate/ma/summaries/`

## Configuration

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

### Customize Styling and Layout (TODO)

Edit `conf/base/parameters.yml`:

```yaml
styling:
  primary_color: "#1F4E79"
  font_family: "Segoe UI"

layout:
  chart_width: 0.6
  summary_width: 0.35

quality_assurance:
  quality_standards: "Professional presentation standards"
  review_criteria: "Accuracy, clarity, visual appeal"
```

### Modify Prompts

Edit prompt files in `data/ppt_generation/prompts/`:
- `ma/` - Multi-agent prompts
- `sa/` - Single-agent prompts

Prompts use placeholders that are filled during agent compilation.

## Project Structure

```
├── conf/
│   ├── base/
│   │   ├── catalog.yml          # Dataset definitions
│   │   ├── parameters.yml       # Pipeline parameters
│   │   └── genai-config.yml     # LLM configuration
│   └── local/                    # Local credentials (gitignored)
│       └── credentials.yml
├── data/
│   ├── ppt_generation/
│   │   ├── sample/               # Input data
│   │   │   ├── slide_generation_requirements.yaml
│   │   │   └── sales_50_products.csv
│   │   ├── prompts/              # Prompt templates
│   │   │   ├── ma/               # Multi-agent prompts (8 files)
│   │   │   └── sa/               # Single-agent prompts (2 files)
│   │   ├── intermediate/         # Intermediate outputs
│   │   │   └── ma/
│   │   │       ├── slide_chart_paths.json
│   │   │       ├── slide_summaries.json
│   │   │       └── slide_configs.json
│   │   └── output/               # Final presentations
│   │       ├── ma/
│   │       └── sa/
├── src/ppt_autogen_workflow/
│   ├── base/
│   │   ├── __init__.py           # Exports base classes and Pydantic models
│   │   └── agent.py              # BaseAgent with structured output support
│   ├── datasets/
│   │   └── autogen_model_client.py  # LLM client dataset
│   ├── pipelines/
│   │   ├── ma_slide_generation_autogen/
│   │   │   ├── agent_planner.py       # PlannerAgent definition
│   │   │   ├── agent_chart.py         # ChartGeneratorAgent definition
│   │   │   ├── agent_summarizer.py    # SummarizerAgent definition
│   │   │   ├── agent_critic.py        # CriticAgent definition
│   │   │   ├── nodes.py               # Pipeline nodes
│   │   │   ├── orchestration_helpers.py  # Helper functions for orchestration
│   │   │   ├── pipeline.py            # Pipeline definition (6 nodes)
│   │   │   └── tools.py               # Agent tool builders
│   │   └── sa_slide_generation_autogen/
│   │       ├── agent.py               # PPTGenerationAgent definition
│   │       ├── agent_helpers.py       # Helper functions for agent operations
│   │       ├── nodes.py               # Pipeline nodes
│   │       ├── pipeline.py            # Pipeline definition (2 nodes)
│   │       └── tools.py               # Agent tool builder
│   └── utils/
│       ├── tools_common.py       # Shared tool implementations
│       ├── node_helpers.py       # Shared node helper functions
│       ├── chart_generator.py    # Chart generation utilities
│       ├── data_analyzer.py      # Data analysis utilities
│       ├── instruction_parser.py # YAML parser
│       ├── ppt_builder.py        # PPT creation utilities
│       └── summary_generator.py  # Summary generation utilities
└── requirements.txt
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

**Matplotlib GUI errors on macOS**
- The code uses 'Agg' backend automatically
- If issues persist, ensure matplotlib is properly installed

**Agent not using tools**
- Check that tools are properly built with sales data
- Verify agent system prompts instruct tool usage
- Review agent response logs for tool invocation

### Debugging

Enable verbose logging:

```bash
kedro run --pipeline=ma_slide_generation_autogen --verbose
```

Check intermediate outputs:
- Requirements: `data/ppt_generation/intermediate/ma/requirements/`
- Charts: `data/ppt_generation/intermediate/ma/charts/`
- Summaries: `data/ppt_generation/intermediate/ma/summaries/`

## Key Design Patterns

### 1. LLM Context Node Pattern
- `llm_context_node` bundles LLM + prompts + tools into `LLMContext` objects
- Reduces pipeline boilerplate (MA: 6 nodes instead of 8, SA: 2 nodes instead of 3)
- `tool()` helper associates tool builder functions with Kedro dataset inputs
- Clean separation of concerns: context creation vs. agent execution

### 2. Shared Utilities
- Common tool implementations in `utils/tools_common.py`
- Common node helpers in `utils/node_helpers.py`
- Eliminates code duplication between MA and SA pipelines

### 3. Prompt Separation
- Prompts stored in YAML files as `LangChainPromptDataset`
- Accessed via `LLMContext.prompts` dictionary
- Easy to modify without code changes

### 4. Tool-Based Data Access
- Sales data captured in tool closures via tool builder functions
- Agents access data through tools, not direct parameters
- Clean separation between data and logic

### 5. Structured Output
- Pydantic models for agent outputs (`ChartOutput`, `SummaryOutput`, `PlanOutput`, `QAFeedbackOutput`)
- Type-safe responses from agents
- Consistent data structures across pipelines

### 6. Agent Specialization (MA)
- Separate agent files: `agent_planner.py`, `agent_chart.py`, `agent_summarizer.py`, `agent_critic.py`
- Each agent has specific role and tools
- Prompts formatted for each agent's needs
- Context passed between agents via orchestration helpers

## License

This project uses the Kedro framework. See [Kedro license](https://github.com/kedro-org/kedro/blob/main/LICENSE.md).
