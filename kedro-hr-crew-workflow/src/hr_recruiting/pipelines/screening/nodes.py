"""Screening pipeline nodes - agentic processing with CrewAI."""

from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext
from kedro.pipeline.preview_contract import MermaidPreview

from hr_recruiting.base.utils import execute_crew_with_retry
from hr_recruiting.pipelines.screening.agents import (
    create_requirements_matcher_agent_with_tools,
    create_resume_evaluator_agent_with_tools,
)
from hr_recruiting.pipelines.screening.helper import (
    build_screening_graph,
    extract_screening_result,
)
from hr_recruiting.pipelines.screening.tasks import (
    create_requirements_matching_task,
    create_resume_evaluation_task,
)


def preview_screening_crew() -> MermaidPreview:
    """Preview function showing context, agents, and tools used in screening workflow."""
    diagram = build_screening_graph()
    
    return MermaidPreview(
        content=diagram,
        meta={
            "flowchart": {
                "wrappingWidth": 250,
                "nodeSpacing": 60,
                "rankSpacing": 70,
            },
             "themeVariables": {
                "lineColor": "#F5A623",
            },
        }
    )


def orchestrate_screening_crew(
    requirements_matcher_context: LLMContext,
    resume_evaluator_context: LLMContext,
) -> dict[str, Any]:
    """Orchestrate CrewAI crew execution for screening workflow."""
    # Create agents with tools
    requirements_matcher = create_requirements_matcher_agent_with_tools(
        requirements_matcher_context
    )
    resume_evaluator = create_resume_evaluator_agent_with_tools(
        resume_evaluator_context
    )

    # Create tasks
    requirements_task = create_requirements_matching_task(
        requirements_matcher_context,
        requirements_matcher,
    )
    evaluation_task = create_resume_evaluation_task(
        resume_evaluator_context,
        resume_evaluator,
    )

    # Create crew with telemetry and tracing disabled
    crew = Crew(
        agents=[requirements_matcher, resume_evaluator],
        tasks=[requirements_task, evaluation_task],
        verbose=True,
        tracing=False,
    )

    # Execute crew with retry logic for connection errors
    crew_result = execute_crew_with_retry(crew)

    # Extract and structure result - strict validation, no fallbacks
    screening_result = extract_screening_result(crew_result)

    return screening_result
