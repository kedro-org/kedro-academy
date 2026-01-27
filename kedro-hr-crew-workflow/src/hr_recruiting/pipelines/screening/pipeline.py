"""Screening pipeline - agentic processing with CrewAI."""

from kedro.pipeline import Pipeline, node
from kedro.pipeline.llm_context import llm_context_node, tool

from hr_recruiting.pipelines.screening.nodes import (
    orchestrate_screening_crew,
    preview_screening_crew,
)
from hr_recruiting.pipelines.screening.tools import (
    build_requirements_matcher_tool,
    build_scoring_tool,
)


def create_pipeline() -> Pipeline:
    """Create screening pipeline with agentic processing."""
    return Pipeline(
        [
            # Create context for requirements matcher agent
            llm_context_node(
                outputs="requirements_matcher_context",
                llm="llm_crew_ai",
                prompts=[
                    "requirements_matcher_agent_system_prompt",
                    "requirements_matching_user_prompt",
                ],
                tools=[
                    tool(
                        build_requirements_matcher_tool,
                        "application",
                        "job_requirements",
                        "matching_config",
                    ),
                ],
                name="create_requirements_matcher_context",
            ),
            # Create context for resume evaluator agent
            llm_context_node(
                outputs="resume_evaluator_context",
                llm="llm_crew_ai",
                prompts=[
                    "resume_evaluator_agent_system_prompt",
                    "resume_evaluation_user_prompt",
                ],
                tools=[
                    tool(
                        build_scoring_tool,
                        "job_requirements",
                        "scoring_config",
                    ),
                ],
                name="create_resume_evaluator_context",
            ),
            # Orchestrate crew execution with contexts
            node(
                func=orchestrate_screening_crew,
                inputs=[
                    "requirements_matcher_context",
                    "resume_evaluator_context",
                ],
                outputs="screening_result",
                name="orchestrate_screening_crew",
                tags=["orchestrator", "agentic"],
                preview_fn=preview_screening_crew,
            ),
        ]
    )
