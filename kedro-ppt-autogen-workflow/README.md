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

2. **Domain Modules** (MA Pipeline): Agent-specific code colocated by domain
   - `chart/`: ChartGeneratorAgent, chart generation logic, and chart tools
   - `summary/`: SummarizerAgent, summary generation logic, and summary tools
   - `planner/`: PlannerAgent, data analysis logic, and planner tools
   - `critic/`: CriticAgent and QA review tools
   - `presentation/`: PPT building utilities (create_slide, combine_presentations)
   - Each module contains `agent.py`, business logic (`generator.py`/`analyzer.py`/`builder.py`), and `tools.py`

3. **Shared Utilities** (`utils/`): True utilities only (no business logic)
   - `fonts.py`: System font detection
   - `instruction_parser.py`: YAML parsing for slide requirements

4. **Base Classes** (`base/`): Shared agent infrastructure
   - `agent.py`: BaseAgent that accepts `LLMContext` directly with class attributes for configuration
   - Output models: `ChartOutput`, `SummaryOutput`, `PlanOutput`, `QAFeedbackOutput`
   - Agents define `agent_name` and `system_prompt_key` as class attributes
   - Simple instantiation: `MyAgent(llm_context).compile()`

5. **Nodes** (`nodes.py`): Kedro pipeline nodes
   - Import from domain modules within the same pipeline
   - Use `LLMContext` to create agents with bundled LLM, prompts, and tools
   - Clear data flow traceability (1 hop within same folder)

6. **Prompts** (`data/ppt_generation/prompts/`): YAML-based prompt templates
   - System prompts define agent behavior
   - User prompts define task instructions
   - Loaded as `LangChainPromptDataset` and accessed via `LLMContext.prompts`

## Pipeline Patterns

### Multi-Agent (MA) Pipeline

**Architecture**: Planner-driven with specialized agents using `llm_context_node`

```
Deterministic Phase:
1. parse_requirements        → Parse YAML into slide configurations

LLM Context Phase:
2. create_planner_context    → Bundle LLM + prompts + tools for Planner
3. create_chart_context      → Bundle LLM + prompts + tools for ChartGenerator
4. create_summarizer_context → Bundle LLM + prompts + tools for Summarizer
5. create_critic_context     → Bundle LLM + prompts + tools for Critic

Agentic Phase:
6. orchestrate_agents        → Create agents from LLMContext, coordinate execution

Deterministic Phase:
7. assemble_presentation     → Combine charts + summaries into slides
```

**Flow**:
- Requirements parsed into structured slide configurations
- LLM contexts bundle model client, prompts, and tools for each agent
- Agents created directly: `ChartGeneratorAgent(llm_context).compile()`
- Planner analyzes requirements, Chart Generator creates charts, Summarizer creates summaries
- Critic reviews slide content for quality
- Final presentation assembled from generated content

**Features**:
- ✅ Clear separation: deterministic vs agentic nodes
- ✅ Quality assurance via Critic agent
- ✅ Specialized agents for each task
- ✅ Simple agent creation from LLMContext
- ✅ Intermediate outputs (charts, summaries) saved

### Single-Agent (SA) Pipeline

**Architecture**: Single agent with all tools using `llm_context_node`

```
Deterministic Phase:
1. parse_requirements      → Parse YAML into slide configurations

LLM Context Phase:
2. create_ppt_context      → Bundle LLM + prompts + tools for PPTGenerator

Agentic Phase:
3. run_ppt_agent           → Create agent from LLMContext, generate charts and summaries

Deterministic Phase:
4. assemble_presentation   → Combine charts + summaries into slides
```

**Flow**:
- Requirements parsed into structured slide configurations
- LLM context bundles model client, prompts, and tools
- Agent created directly: `PPTGenerationAgent(llm_context).compile()`
- Single agent generates charts and summaries using tools
- Final presentation assembled from generated content

**Features**:
- ✅ Clear separation: deterministic vs agentic nodes
- ✅ Simpler architecture (4 nodes)
- ✅ Faster execution
- ✅ Simple agent creation from LLMContext
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

# Prompts are also defined here (not in catalog.yml)
ppt_generator_system_prompt:
  type: kedro_datasets_experimental.langchain.LangChainPromptDataset
  filepath: data/ppt_generation/prompts/sa/ppt_generator_system.yml
  template: ChatPromptTemplate
  dataset:
    type: yaml.YAMLDataset
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
│   │   │   ├── chart/                 # Chart generation domain module
│   │   │   │   ├── __init__.py        # Exports agent, generator, tools
│   │   │   │   ├── agent.py           # ChartGeneratorAgent
│   │   │   │   ├── generator.py       # Chart generation logic
│   │   │   │   └── tools.py           # Chart tools for agent
│   │   │   ├── summary/               # Summary generation domain module
│   │   │   │   ├── __init__.py        # Exports agent, generator, tools
│   │   │   │   ├── agent.py           # SummarizerAgent
│   │   │   │   ├── generator.py       # Summary generation logic
│   │   │   │   └── tools.py           # Summary tools for agent
│   │   │   ├── planner/               # Planning domain module
│   │   │   │   ├── __init__.py        # Exports agent, analyzer, tools
│   │   │   │   ├── agent.py           # PlannerAgent
│   │   │   │   ├── analyzer.py        # Data analysis logic
│   │   │   │   └── tools.py           # Planner tools for agent
│   │   │   ├── critic/                # QA domain module
│   │   │   │   ├── __init__.py        # Exports agent, tools
│   │   │   │   ├── agent.py           # CriticAgent + run_qa_review
│   │   │   │   └── tools.py           # QA review tools
│   │   │   ├── presentation/          # PPT building module
│   │   │   │   ├── __init__.py        # Exports builder functions
│   │   │   │   └── builder.py         # create_slide, combine_presentations
│   │   │   ├── nodes.py               # Pipeline nodes (imports from modules)
│   │   │   ├── orchestration_helpers.py  # Prompt formatting helpers
│   │   │   └── pipeline.py            # Pipeline definition (7 nodes)
│   │   └── sa_slide_generation_autogen/
│   │       ├── agent.py               # PPTGenerationAgent definition
│   │       ├── agent_helpers.py       # Helper functions (imports from MA modules)
│   │       ├── nodes.py               # Pipeline nodes
│   │       ├── pipeline.py            # Pipeline definition (4 nodes)
│   │       └── tools.py               # Tools (imports from MA modules)
│   └── utils/                         # True utilities only
│       ├── fonts.py              # System font detection
│       └── instruction_parser.py # YAML parser for slide requirements
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
- `tool()` helper associates tool builder functions with Kedro dataset inputs
- Clean separation of concerns: context creation vs. agent execution

### 2. Simple Agent Creation
- Agents accept `LLMContext` directly in constructor
- Configuration via class attributes (`agent_name`, `system_prompt_key`)
- One-liner instantiation: `MyAgent(llm_context).compile()`
- No factory functions needed - just use the class constructor

### 3. Deterministic vs Agentic Separation
- **Deterministic nodes**: `parse_requirements`, `assemble_presentation` (no LLM calls)
- **LLM context nodes**: Bundle LLM + prompts + tools
- **Agentic nodes**: `run_ppt_agent`, `orchestrate_agents` (LLM-powered)
- Clear boundaries make testing and debugging easier

### 4. Domain Module Architecture (MA Pipeline)
- Agent-specific code colocated by domain (`chart/`, `summary/`, `planner/`, `critic/`, `presentation/`)
- Each module contains: `agent.py`, business logic file, and `tools.py`
- Clear data flow traceability: trace imports within same folder (1 hop vs 4 hops before)
- SA pipeline reuses logic via imports from MA modules

### 5. Configuration Separation
- **`catalog.yml`**: Data catalog (input, intermediate, output datasets)
- **`genai-config.yml`**: GenAI config (LLM client + prompt datasets)
- **`parameters.yml`**: Pipeline parameters (styling, layout, QA settings)
- Prompts and LLM config kept together for easier management

### 6. Prompt Separation
- Prompts stored in YAML files as `LangChainPromptDataset`
- Accessed via `LLMContext.prompts` dictionary
- Easy to modify without code changes

### 7. Tool-Based Data Access
- Sales data captured in tool closures via tool builder functions
- Agents access data through tools, not direct parameters
- Clean separation between data and logic

### 8. Structured Output
- Pydantic models for agent outputs (`ChartOutput`, `SummaryOutput`, `PlanOutput`, `QAFeedbackOutput`)
- Type-safe responses from agents
- Consistent data structures across pipelines

### 9. Error Handling
- Chart generation raises `ChartGenerationError` on failure (no silent fallbacks)
- Summary generation has graceful fallbacks with logging
- Clear error messages with context for debugging

## License

This project uses the Kedro framework. See [Kedro license](https://github.com/kedro-org/kedro/blob/main/LICENSE.md).
