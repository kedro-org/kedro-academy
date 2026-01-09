"""Multi-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    init_tools,
    initialize_planner_agent,
    initialize_chart_generator_agent,
    initialize_summarizer_agent,
    initialize_critic_agent,
    orchestrate_multi_agent_workflow
)


def create_pipeline(**kwargs) -> Pipeline:
    """
    Create the multi-agent PPT generation pipeline with explicit data flow.
    
    Each agent receives specific prompts, LLM client, and required data,
    making the data flow explicit and following kedro agentic workflow best practices.
    
    Data Flow:
    1. Load prompt datasets for each agent type
    2. Initialize agents with compiled prompts and specific data requirements
    3. Orchestrate multi-agent collaboration with clear inputs/outputs
    
    Returns:
        Pipeline object with explicit agent initialization and orchestration nodes
    """
    return pipeline([
        # Initialize Tools Dictionary
        node(
            func=init_tools,
            inputs=["sales_data"],
            outputs="tools",
            name="init_tools_node",
            tags=["autogen", "tools"],
        ),
        
        # Initialize Agents with Explicit Prompts and Tools from Dictionary
        node(
            func=initialize_planner_agent,
            inputs=[
                "llm_autogen",              # LLM client for planner
                "planner_system_prompt",    # Planner-specific system prompt
                "tools"                     # Tools dictionary
            ],
            outputs="compiled_planner_agent",
            name="compile_planner_agent",
            tags=["autogen", "compilation", "planner", "multi_agent"],
        ),
        
        node(
            func=initialize_chart_generator_agent,
            inputs=[
                "llm_autogen",                      # LLM client for chart generation
                "chart_generator_system_prompt",   # Chart generator-specific system prompt
                "tools"                             # Tools dictionary
            ],
            outputs="compiled_chart_agent",
            name="compile_chart_generator_agent",
            tags=["autogen", "compilation", "chart_generator", "multi_agent"],
        ),
        
        node(
            func=initialize_summarizer_agent,
            inputs=[
                "llm_autogen",                  # LLM client for summarization
                "summarizer_system_prompt",    # Summarizer-specific system prompt
                "tools"                         # Tools dictionary
            ],
            outputs="compiled_summarizer_agent",
            name="compile_summarizer_agent", 
            tags=["autogen", "compilation", "summarizer", "multi_agent"],
        ),
        
        node(
            func=initialize_critic_agent,
            inputs=[
                "llm_autogen",              # LLM client for quality assessment
                "critic_system_prompt",    # Critic-specific system prompt
                "tools"                     # Tools dictionary
            ],
            outputs="compiled_critic_agent",
            name="compile_critic_agent",
            tags=["autogen", "compilation", "critic", "multi_agent"],
        ),
        
        # Orchestrate multi-agent workflow with explicit data dependencies
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "compiled_planner_agent",      # Agent: Planning and coordination
                "compiled_chart_agent",        # Agent: Chart generation
                "compiled_summarizer_agent",   # Agent: Content summarization  
                "compiled_critic_agent",       # Agent: Quality assurance
                "planner_user_prompt",         # Prompt: Planner user queries
                "chart_generator_user_prompt", # Prompt: Chart generator user queries
                "summarizer_user_prompt",      # Prompt: Summarizer user queries
                "critic_user_prompt",          # Prompt: Critic user queries
                "instructions_yaml",           # Data: Slide generation instructions
                "sales_data",                  # Data: Source data for analysis
                "params:user_query"            # Parameter: User request context
            ],
            outputs=["final_presentation", "slide_charts", "slide_summaries"],
            name="orchestrate_agents",
            tags=["autogen", "orchestration", "multi_agent"],
        ),
    ])