# PR #97: Add Multi-Agent (MA) PPT generation pipeline

## Summary

- Implements multi-agent PPT generation pipeline using specialized agents
- Uses Kedro's `llm_context_node` pattern to bundle LLM + prompts + tools
- Organizes code into domain modules for clear traceability (chart/, summary/, planner/, critic/, presentation/)
- Pipeline structure: 6 nodes (4 context nodes + orchestration + assembly)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Pipeline (6 nodes)               │
├─────────────────────────────────────────────────────────────────┤
│  1. create_planner_context    → LLMContext for Planner          │
│  2. create_chart_context      → LLMContext for ChartGenerator   │
│  3. create_summarizer_context → LLMContext for Summarizer       │
│  4. create_critic_context     → LLMContext for Critic           │
│  5. orchestrate_agents        → Run workflow, generate content  │
│  6. assemble_presentation     → Combine into final PowerPoint   │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Module Structure

Each agent has its code colocated in a domain module for clear traceability:

```
ma_slide_generation_autogen/
├── chart/                    # Chart generation domain
│   ├── __init__.py          # Exports: ChartGeneratorAgent, generate_chart, build_chart_generator_tools
│   ├── agent.py             # ChartGeneratorAgent class + generate_chart()
│   ├── generator.py         # Chart rendering logic (bar, pie, line charts)
│   └── tools.py             # FunctionTools for chart generation
├── summary/                  # Summary generation domain
│   ├── __init__.py
│   ├── agent.py             # SummarizerAgent class + generate_summary()
│   ├── generator.py         # Summary text generation logic
│   └── tools.py             # FunctionTools for summary generation
├── planner/                  # Planning domain
│   ├── __init__.py
│   ├── agent.py             # PlannerAgent class
│   ├── analyzer.py          # Data analysis logic
│   └── tools.py             # FunctionTools for data analysis
├── critic/                   # QA review domain
│   ├── __init__.py
│   ├── agent.py             # CriticAgent class + run_qa_review()
│   └── tools.py             # FunctionTools for QA review
├── presentation/             # PPT building domain
│   ├── __init__.py
│   └── builder.py           # create_slide(), combine_presentations()
├── nodes.py                  # Pipeline node functions
├── orchestration_helpers.py  # Agent creation and prompt formatting
└── pipeline.py               # Pipeline definition with llm_context_node
```

## Key Design Decisions

### 1. Domain Module Architecture
- **Before**: Agent code in separate files, business logic in `utils/` (4 hops to trace)
- **After**: All agent-related code in same folder (1 hop to trace)
- Addresses reviewer feedback: "I find the structure with so many things in utils hard to navigate"

### 2. llm_context_node Pattern
```python
llm_context_node(
    outputs="chart_context",
    llm="llm_autogen",
    prompts=["chart_generator_system_prompt", "chart_generator_user_prompt"],
    tools=[tool(build_chart_generator_tools, "sales_data")],
    name="create_chart_context",
)
```
- Bundles LLM + prompts + tools into single `LLMContext` object
- Reduces boilerplate compared to separate init_tools/compile nodes

### 3. Separation of Concerns
- **Orchestration node**: Agent creation, workflow execution, content generation
- **Assembly node**: Deterministic slide creation from generated content (no LLM calls)

## Agent Roles

| Agent | Role | Tools |
|-------|------|-------|
| Planner | Analyzes requirements, plans workflow | `analyze_sales_data` |
| ChartGenerator | Creates data visualizations | `generate_sales_chart` |
| Summarizer | Generates bullet-point summaries | `generate_business_summary` |
| Critic | Reviews quality, provides feedback | `review_slide_content` |

## Test Plan

- [ ] Run `kedro run --pipeline=ma_slide_generation_autogen`
- [ ] Verify all 4 agents are created and invoked
- [ ] Check generated charts exist and are valid PNG files
- [ ] Validate summaries contain actual data values (not placeholders)
- [ ] Confirm final presentation has correct number of slides

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
