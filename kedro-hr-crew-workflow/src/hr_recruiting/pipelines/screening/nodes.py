"""Screening pipeline nodes - agentic processing with CrewAI."""

from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext
from kedro.pipeline.preview_contract import MermaidPreview

from hr_recruiting.base.utils import execute_crew_with_retry
from hr_recruiting.pipelines.screening.agents import (
    create_requirements_matcher_agent,
    create_resume_evaluator_agent,
)
from hr_recruiting.pipelines.screening.helper import (
    _extract_single_task_output,
    build_screening_graph,
    calculate_scoring_result,
    merge_screening_result,
)
from hr_recruiting.pipelines.screening.models import (
    RequirementsMatchingResult,
    ScreeningEvaluationOutput,
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
    scoring_config: dict[str, Any],
    crew_config: dict[str, Any],
) -> dict[str, Any]:
    """Orchestrate screening in two phases: match, score, then LLM evaluate."""
    requirements_matcher_agent = create_requirements_matcher_agent(
        requirements_matcher_context
    )
    resume_evaluator_agent = create_resume_evaluator_agent(
        resume_evaluator_context
    )

    requirements_matching_task = create_requirements_matching_task(
        requirements_matcher_context,
        requirements_matcher_agent,
    )

    matching_crew = Crew(
        agents=[requirements_matcher_agent],
        tasks=[requirements_matching_task],
        verbose=crew_config["verbose"],
        tracing=crew_config["tracing"],
    )
    matching_crew_result = execute_crew_with_retry(matching_crew)
    matching_outputs = matching_crew_result.tasks_output if hasattr(
        matching_crew_result, "tasks_output"
    ) else []
    if not matching_outputs:
        raise ValueError("No output from requirements matching crew")

    matching_result = _extract_single_task_output(
        matching_outputs[0],
        RequirementsMatchingResult,
    )
    scoring_result = calculate_scoring_result(matching_result, scoring_config)

    evaluation_task = create_resume_evaluation_task(
        resume_evaluator_context,
        resume_evaluator_agent,
        matching_result,
        scoring_result,
    )
    evaluation_crew = Crew(
        agents=[resume_evaluator_agent],
        tasks=[evaluation_task],
        verbose=crew_config["verbose"],
        tracing=crew_config["tracing"],
    )
    evaluation_crew_result = execute_crew_with_retry(evaluation_crew)
    evaluation_outputs = evaluation_crew_result.tasks_output if hasattr(
        evaluation_crew_result, "tasks_output"
    ) else []
    if not evaluation_outputs:
        raise ValueError("No output from resume evaluation crew")

    evaluation_result = _extract_single_task_output(
        evaluation_outputs[0],
        ScreeningEvaluationOutput,
    )

    return merge_screening_result(
        matching_result,
        scoring_result,
        evaluation_result,
    )
