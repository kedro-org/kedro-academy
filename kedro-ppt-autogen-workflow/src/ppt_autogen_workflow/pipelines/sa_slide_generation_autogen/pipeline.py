"""Single-agent AutoGen PPT generation pipeline.

This pipeline demonstrates clear separation between:
1. Deterministic data preparation (parse_requirements)
2. LLM context assembly (llm_context_node)
3. Agentic content generation (run_ppt_agent)
4. Deterministic presentation assembly (assemble_presentation)
"""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import parse_requirements, run_ppt_agent, assemble_presentation
from .tools import build_tools


def create_pipeline(**kwargs) -> Pipeline:
    """Create the single-agent AutoGen PPT generation pipeline.

    Pipeline structure (4 nodes):
        1. parse_requirements: Parse YAML requirements (deterministic)
        2. llm_context_node: Bundle LLM + prompts + tools into LLMContext
        3. run_ppt_agent: Generate charts and summaries (agentic)
        4. assemble_presentation: Create final PowerPoint (deterministic)
    """
    return pipeline([
        # Step 1: Parse requirements (deterministic)
        node(
            func=parse_requirements,
            inputs="slide_generation_requirements",
            outputs="sa_slide_configs",
            name="parse_requirements",
            tags=["deterministic", "data_preparation"],
        ),
        # Step 2: Create LLM context
        llm_context_node(
            outputs="ppt_llm_context",
            llm="llm_autogen",
            prompts=[
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
            ],
            tools=[tool(build_tools, "sales_data")],
            name="create_ppt_context",
        ),
        # Step 3: Run agent (agentic)
        node(
            func=run_ppt_agent,
            inputs=[
                "ppt_llm_context",
                "sa_slide_configs",
            ],
            outputs="sa_slide_content",
            name="run_ppt_agent",
            tags=["autogen", "agentic", "single_agent"],
        ),
        # Step 4: Assemble presentation (deterministic)
        node(
            func=assemble_presentation,
            inputs="sa_slide_content",
            outputs="sales_analysis_sa",
            name="assemble_presentation",
            tags=["deterministic", "assembly"],
        ),
    ])
