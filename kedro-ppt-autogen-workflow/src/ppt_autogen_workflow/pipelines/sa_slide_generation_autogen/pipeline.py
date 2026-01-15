"""Single-agent AutoGen pipeline"""

from kedro.pipeline import Pipeline, pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from .nodes import run_ppt_agent

# Import shared tool builder from base
from ppt_autogen_workflow.base.tools import build_sa_tools
# Import preprocessing and postprocessing from base
from ppt_autogen_workflow.base.postprocessing import assemble_presentation
from .nodes import parse_sa_slide_requirements


def create_pipeline() -> Pipeline:
    """Create the single-agent AutoGen pipeline with preprocessing and postprocessing."""
    return pipeline([
        # Preprocessing: Parse slide requirements
        node(
            func=parse_sa_slide_requirements,
            inputs="slide_generation_requirements",
            outputs="sa_slide_configs",
            name="sa_parse_slide_requirements",
            tags=["preprocessing", "deterministic", "requirements_parsing"],
        ),

        # Step 1: Create LLM context
        # Single agent gets all tools bundled together
        llm_context_node(
            outputs="ppt_llm_context",
            llm="llm_autogen",
            prompts=[
                "ppt_generator_system_prompt",
                "ppt_generator_user_prompt",
            ],
            tools=[tool(build_sa_tools, "sales_data", "params:styling")],
            name="sa_create_ppt_context",
        ),

        # Step 2: Run single agent
        node(
            func=run_ppt_agent,
            inputs=[
                "ppt_llm_context",
                "sa_slide_configs",
            ],
            outputs="sa_slide_content",
            name="sa_run_ppt_agent",
            tags=["sa_autogen", "agentic"],
        ),

        # Postprocessing: Assemble presentation
        node(
            func=assemble_presentation,
            inputs=[
                "sa_slide_content",
                "params:layout",
                "params:styling",
            ],
            outputs="sales_analysis_sa",
            name="sa_assemble_presentation",
            tags=["postprocessing", "deterministic", "presentation_assembly"],
        ),
    ])
