# Architecture

## Overview

This project generates PowerPoint presentations from structured YAML instructions using AutoGen agents and utility functions. It provides two pipeline approaches: **Multi-Agent (MA)** and **Single-Agent (SA)**.

## Pipeline Architecture

### Multi-Agent Pipeline (`ma_slide_generation_autogen`)

**Purpose**: Orchestrated workflow with specialized agents collaborating to create presentations.

**Flow**:
```
┌─────────────┐
│ llm_autogen │
└──────┬──────┘
       │
       ├───► PlannerAgent ────┐
       ├───► ChartGenerator ──┤
       ├───► Summarizer ──────┼──► Orchestrator ──► Final Presentation
       └───► CriticAgent ─────┘
```

**Components**:
1. **PlannerAgent**: Analyzes requirements and creates plan
2. **ChartGeneratorAgent**: Generates data visualizations
3. **SummarizerAgent**: Creates slide summaries
4. **CriticAgent**: Quality assurance and feedback

**Process**:
1. Parse `instructions_yaml` to extract slide definitions
2. For each slide:
   - Planner analyzes requirements
   - ChartGenerator creates chart using utility functions
   - Summarizer creates summary using utility functions
   - Critic reviews and provides QA score
3. Combine all slides into final presentation
4. Save intermediate charts (PNG) and summaries (TXT) to `data/02_intermediate`

**Outputs**:
- `final_presentation`: Combined PowerPoint presentation
- `slide_charts`: Partition dataset with PNG files
- `slide_summaries`: Partition dataset with TXT files

### Single-Agent Pipeline (`sa_slide_generation_autogen`)

**Purpose**: Simplified workflow using a single agent with direct utility function calls.

**Flow**:
```
┌─────────────┐
│ llm_autogen │
└──────┬──────┘
       │
       └───► PPTGenerationAgent ──► Orchestrator ──► Final Presentation
```

**Components**:
1. **PPTGenerationAgent**: Single agent

**Process**:
1. Parse `instructions_yaml` to extract slide definitions
2. For each slide:
   - Generate chart using utility functions directly
   - Generate summary using utility functions directly
3. Combine all slides into final presentation

**Outputs**:
- `final_presentation`: Combined PowerPoint presentation

## Key Design Decisions

### Structured Processing
Both pipelines parse `instructions_yaml` programmatically rather than relying on LLM interpretation, ensuring deterministic slide generation.

### Utility Functions
Core functionality (chart generation, summary generation, slide creation) is implemented as pure utility functions, making them:
- Testable
- Reusable
- Deterministic

### Agent Architecture
Agents are initialized and available for future extensibility, but current implementation uses utility functions directly for reliability.

### Partition Datasets
Intermediate outputs (charts, summaries) use Kedro partition datasets, enabling:
- Dynamic number of slides
- Individual file inspection
- No manual catalog updates

## Data Flow

```
instructions.yaml ──┐
                    ├──► Parse Structure ──► Extract Slide Definitions
sales_data.csv ─────┘
                    │
                    ├──► For Each Slide:
                    │   ├──► Generate Chart (utility function)
                    │   ├──► Generate Summary (utility function)
                    │   └──► Create Slide (utility function)
                    │
                    └──► Combine Slides ──► final_presentation.pptx
```

## File Structure

```
src/ppt_autogen_workflow/
|── datasets/
|   ├── autogen_model_client.py
├── pipelines/
│   ├── ma_slide_generation_autogen/    # Multi-agent pipeline
│   │   ├── agent.py                   # Agent definitions
│   │   ├── nodes.py                    # Pipeline nodes
│   │   ├── pipeline.py                 # Pipeline definition
│   │   └── tools.py                    # Agent tools
│   └── sa_slide_generation_autogen/    # Single-agent pipeline
│       ├── agent.py                    # Agent definition
│       ├── nodes.py                    # Pipeline nodes
│       ├── pipeline.py                 # Pipeline definition
│       └── tools.py                    # Agent tools
└── utils/
    ├── chart_generator.py              # Chart generation utilities
    ├── summary_generator.py            # Summary generation utilities
    └── ppt_builder.py                  # Slide creation utilities
```

## Configuration

- **Catalog** (`conf/base/catalog.yml`): Dataset definitions
- **Parameters** (`conf/base/parameters.yml`): User query and settings
- **GenAI Config** (`conf/base/genai-config.yml`): LLM configuration
- **Credentials** (`conf/local/credentials.yml`): API keys (not in repo)

