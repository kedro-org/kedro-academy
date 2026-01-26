"""Applications pipeline - agentic processing with CrewAI."""

from kedro.pipeline import Pipeline, llm_context_node, node

from hr_recruiting.pipelines.applications.nodes import (
    parse_resume_text,
    run_resume_parsing_crew,
    split_resume_parsing_result,
)


def create_pipeline() -> Pipeline:
    """Create the applications pipeline with agentic processing.

    This pipeline handles agentic processing of resumes:
    1. Parse raw resume document (extract text)
    2. Create LLM context for resume parser agent
    3. Run CrewAI crew execution for parsing and normalization
    4. Output normalized candidate profile and evidence snippets

    Returns:
        Configured Pipeline object
    """
    return Pipeline(
        [
            # Parse raw resume (extract text only - deterministic)
            node(
                func=parse_resume_text,
                inputs="raw_resume",
                outputs="parsed_resume",
                name="parse_resume_text",
            ),
            # Create context for resume parser agent
            llm_context_node(
                outputs="resume_parser_context",
                llm="llm_crew_ai",
                prompts=[
                    "resume_parser_agent_system_prompt",
                    "resume_parsing_user_prompt",
                ],
                tools=[],
                name="create_resume_parser_context",
            ),
            # Run crew execution with context
            node(
                func=run_resume_parsing_crew,
                inputs=[
                    "resume_parser_context",
                    "parsed_resume",
                    "resume_parsing_schema_template",
                ],
                outputs="resume_parsing_result",
                name="run_resume_parsing_crew",
                tags=["agentic"],
            ),
            # Split result into separate outputs
            node(
                func=split_resume_parsing_result,
                inputs="resume_parsing_result",
                outputs=["normalized_candidate_profile", "evidence_snippets"],
                name="split_resume_parsing_result",
            ),
        ]
    )
