"""Screening pipeline - agentic processing with CrewAI."""

from kedro.pipeline import Pipeline, llm_context_node, node, tool

from hr_recruiting.pipelines.screening.nodes import orchestrate_screening_crew
from hr_recruiting.pipelines.screening.tools import (
    build_email_draft_tool,
    build_policy_check_tool,
    build_requirements_matcher_tool,
    build_scoring_tool,
)


def create_pipeline() -> Pipeline:
    """Create screening pipeline with agentic processing."""
    from hr_recruiting.pipelines.screening.helper import create_application
    
    return Pipeline(
        [
            # Create Application object from candidate profile and job posting
            node(
                func=create_application,
                inputs=[
                    "normalized_candidate_profile",
                    "normalized_job_posting",
                ],
                outputs="application",
                name="create_application",
            ),
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
                        "normalized_job_posting",
                        "evidence_snippets",
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
                        "normalized_job_posting",
                        "scoring_config",
                    ),
                    tool(
                        build_policy_check_tool,
                        "policy_rules",
                    ),
                ],
                name="create_resume_evaluator_context",
            ),
            # Create context for communications drafter agent
            llm_context_node(
                outputs="comms_drafter_context",
                llm="llm_crew_ai",
                prompts=[
                    "comms_drafter_agent_system_prompt",
                    "email_draft_user_prompt",
                ],
                tools=[
                    tool(
                        build_email_draft_tool,
                        "application",
                        "email_templates",
                    ),
                    tool(
                        build_policy_check_tool,
                        "policy_rules",
                    ),
                ],
                name="create_comms_drafter_context",
            ),
            # Orchestrate crew execution with all contexts
            node(
                func=orchestrate_screening_crew,
                inputs=[
                    "requirements_matcher_context",
                    "resume_evaluator_context",
                    "comms_drafter_context",
                ],
                outputs="screening_result",
                name="orchestrate_screening_crew",
                tags=["orchestrator", "agentic"],
            ),
        ]
    )
