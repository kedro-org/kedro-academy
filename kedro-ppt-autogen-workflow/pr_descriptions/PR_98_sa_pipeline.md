# PR #98: Add Single-Agent (SA) PPT generation pipeline

## Summary

- Implements single-agent PPT generation pipeline as a simpler alternative to MA
- Uses Kedro's `llm_context_node` pattern for consistency with MA pipeline
- Reuses business logic from MA pipeline's domain modules (DRY principle)
- Pipeline structure: 2 nodes (context creation + presentation generation)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Single-Agent Pipeline (2 nodes)              │
├─────────────────────────────────────────────────────────────────┤
│  1. create_ppt_context       → LLMContext for PPTGenerator      │
│  2. generate_presentation    → Create agent, generate all slides│
└─────────────────────────────────────────────────────────────────┘
```

## Key Differences from MA Pipeline

| Aspect | MA Pipeline | SA Pipeline |
|--------|-------------|-------------|
| Agents | 4 specialized agents | 1 general-purpose agent |
| Nodes | 6 nodes | 2 nodes |
| QA Review | Yes (Critic agent) | No |
| Complexity | Higher | Lower |
| Execution | Sequential agent handoffs | Single agent with all tools |

## Code Structure

```
sa_slide_generation_autogen/
├── agent.py              # PPTGenerationAgent class
├── agent_helpers.py      # generate_chart(), generate_summary(), create_slide_presentation()
├── nodes.py              # generate_presentation() node function
├── pipeline.py           # Pipeline definition with llm_context_node
└── tools.py              # Tool builders (imports logic from MA modules)
```

## Code Reuse Strategy

SA pipeline imports shared logic from MA pipeline's domain modules:

```python
# In sa_slide_generation_autogen/tools.py
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.planner.analyzer import (
    analyze_sales_data_json,
)
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.chart.generator import (
    generate_chart_figure,
)
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.summary.generator import (
    generate_summary_text,
)

# In sa_slide_generation_autogen/nodes.py
from ppt_autogen_workflow.pipelines.ma_slide_generation_autogen.presentation import (
    combine_presentations,
    format_summary_text,
)
```

This approach:
- Eliminates code duplication between pipelines
- Ensures consistent behavior for chart/summary generation
- MA modules serve as the "source of truth" for business logic

## PPTGenerationAgent

Single agent with all capabilities:

```python
class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    async def invoke_for_chart(self, query: str) -> ChartOutput
    async def invoke_for_summary(self, query: str) -> SummaryOutput
```

**Available Tools:**
- `analyze_sales_data`: Data analysis and insights
- `generate_sales_chart`: Chart visualization creation
- `generate_business_summary`: Bullet-point summary generation
- `validate_slide_parameters`: Slide parameter validation

## When to Use SA vs MA

**Use SA Pipeline when:**
- Quick prototyping or testing
- Simple presentations with few slides
- QA review not required
- Faster execution needed

**Use MA Pipeline when:**
- Production-quality presentations
- Quality assurance is important
- Complex multi-slide presentations
- Specialized agent reasoning needed

## Test Plan

- [ ] Run `kedro run --pipeline=sa_slide_generation_autogen`
- [ ] Verify single agent handles chart and summary generation
- [ ] Check output presentation matches expected slide count
- [ ] Compare output quality with MA pipeline
- [ ] Validate imports from MA modules work correctly

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
