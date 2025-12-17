"""Single-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import initialize_ppt_agent, run_ppt_generation


def create_pipeline(**kwargs) -> Pipeline:
    """
    Create the single-agent AutoGen PPT generation pipeline.
    
    Parses instructions_yaml and generates slides programmatically using utility functions.
    Agent is initialized for future extensibility but not actively used.
    
    Returns:
        Pipeline object with compile and generation nodes
    """
    return pipeline([
        node(
            func=initialize_ppt_agent,
            inputs=["llm_autogen", "sales_data"],
            outputs="compiled_ppt_agent",
            name="compile_ppt_agent",
            tags=["autogen", "compilation", "agent", "single_agent"],
        ),
        node(
            func=run_ppt_generation,
            inputs=["compiled_ppt_agent", "instructions_yaml", "sales_data", "params:user_query"],
            outputs="final_presentation",
            name="invoke_ppt_generation",
            tags=["autogen", "invocation", "generation", "single_agent"],
        ),
    ])