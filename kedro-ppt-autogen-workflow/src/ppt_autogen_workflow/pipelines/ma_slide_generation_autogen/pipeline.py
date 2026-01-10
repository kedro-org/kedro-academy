"""Multi-agent AutoGen PPT generation pipeline."""

from kedro.pipeline import Pipeline, pipeline, node

from .nodes import (
    init_tools,
    analyze_requirements,
    compile_planner_agent,
    compile_chart_generator_agent,
    compile_summarizer_agent,
    compile_critic_agent,
    orchestrate_multi_agent_workflow
)


def create_pipeline(**kwargs) -> Pipeline:
    """
    Create the multi-agent PPT generation pipeline with planner-driven architecture.

    Architecture:
    - PLANNER analyzes requirements and creates instructions for all agents
    - OTHER AGENTS receive planner's analysis and execute their specialized tasks
    - ORCHESTRATOR only coordinates round-robin execution

    Data Flow:
    1. sales_data → init_tools → tools

    2. slide_generation_requirements + params:styling + params:layout
       → analyze_requirements
       → (planner_requirement, chart_requirement, summarizer_requirement)

    3. planner_system_prompt + planner_requirement + llm_autogen + tools
       → compile_planner_agent → compiled_planner_agent

    4. chart_requirement + chart_generator_system_prompt + chart_generator_user_prompt
       + llm_autogen + tools → compile_chart_generator_agent
       → compiled_chart_agent (with formatted prompts stored internally)

    5. summarizer_requirement + summarizer_system_prompt + summarizer_user_prompt
       + llm_autogen + tools → compile_summarizer_agent
       → compiled_summarizer_agent (with formatted prompts stored internally)

    6. critic_system_prompt + critic_user_prompt + params:quality_assurance
       + llm_autogen + tools → compile_critic_agent
       → compiled_critic_agent (with template and quality params stored internally)

    7. All compiled agents → orchestrate_agents
       → (final_presentation, slide_charts, slide_summaries)
       (orchestrator uses pre-formatted prompts from agents)

    Returns:
        Pipeline object with planner-driven architecture
    """
    return pipeline([
        # Step 1: Initialize tools with sales data
        node(
            func=init_tools,
            inputs=["sales_data"],
            outputs="tools",
            name="init_tools_node",
            tags=["tools"],
        ),

        # Step 2: Analyze requirements and create agent-specific requirements
        node(
            func=analyze_requirements,
            inputs=[
                "slide_generation_requirements",  # User requirements (YAML)
                "params:styling",                 # Styling parameters
                "params:layout",                  # Layout parameters
            ],
            outputs=["planner_requirements", "chart_requirements", "summarizer_requirements"],
            name="analyze_requirements",
            tags=["analysis", "requirements"],
        ),

        # Step 3: Compile Planner Agent
        node(
            func=compile_planner_agent,
            inputs=[
                "planner_system_prompt",          # System instructions for planning
                "planner_requirements",            # Planner requirement object
                "llm_autogen",                    # LLM client
                "tools",                          # Tools with data access
            ],
            outputs="compiled_planner_agent",
            name="compile_planner_agent",
            tags=["autogen", "compilation", "planner"],
        ),

        # Step 4: Compile Chart Generator Agent
        node(
            func=compile_chart_generator_agent,
            inputs=[
                "chart_requirements",              # Chart requirement object
                "chart_generator_system_prompt", # Chart generator system prompt
                "chart_generator_user_prompt",   # Chart generator user template
                "llm_autogen",                   # LLM client
                "tools",                         # Tools with data access
            ],
            outputs="compiled_chart_agent",
            name="compile_chart_generator_agent",
            tags=["autogen", "compilation", "chart_generator"],
        ),

        # Step 5: Compile Summarizer Agent
        node(
            func=compile_summarizer_agent,
            inputs=[
                "summarizer_requirements",         # Summarizer requirement object
                "summarizer_system_prompt",       # Summarizer system prompt
                "summarizer_user_prompt",         # Summarizer user template
                "llm_autogen",                   # LLM client
                "tools",                         # Tools with data access
            ],
            outputs="compiled_summarizer_agent",
            name="compile_summarizer_agent",
            tags=["autogen", "compilation", "summarizer"],
        ),

        # Step 6: Compile Critic Agent
        node(
            func=compile_critic_agent,
            inputs=[
                "critic_system_prompt",           # Critic system prompt
                "critic_user_prompt",             # Critic user template
                "params:quality_assurance",        # Quality assurance parameters
                "llm_autogen",                   # LLM client
                "tools",                         # Tools with data access
            ],
            outputs="compiled_critic_agent",
            name="compile_critic_agent",
            tags=["autogen", "compilation", "critic"],
        ),

        # Step 7: Orchestrate - lightweight round-robin coordinator
        node(
            func=orchestrate_multi_agent_workflow,
            inputs=[
                "compiled_planner_agent",        # Planner agent
                "compiled_chart_agent",          # Chart generator agent (with formatted prompts)
                "compiled_summarizer_agent",     # Summarizer agent (with formatted prompts)
                "compiled_critic_agent",         # Critic agent (with template and quality params)
            ],
            outputs=["sales_analysis", "slide_charts", "slide_summaries"],
            name="orchestrate_agents",
            tags=["autogen", "orchestration"],
        ),
    ])