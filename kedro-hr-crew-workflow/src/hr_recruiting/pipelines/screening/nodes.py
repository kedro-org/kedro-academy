"""Screening pipeline nodes - agentic processing with CrewAI."""

import os
from typing import Any

from crewai import Crew
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.utils import execute_crew_with_retry
from hr_recruiting.pipelines.screening.agents import (
    create_comms_drafter_agent_with_tools,
    create_requirements_matcher_agent_with_tools,
    create_resume_evaluator_agent_with_tools,
)
from hr_recruiting.pipelines.screening.helper import extract_screening_result
from hr_recruiting.pipelines.screening.tasks import (
    create_email_draft_task,
    create_requirements_matching_task,
    create_resume_evaluation_task,
)

# Disable CrewAI telemetry to avoid connection errors
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"


def orchestrate_screening_crew(
    requirements_matcher_context: LLMContext,
    resume_evaluator_context: LLMContext,
    comms_drafter_context: LLMContext,
) -> dict[str, Any]:
    """Orchestrate CrewAI crew execution for screening workflow.

    This node creates agents, tasks, and crew, then executes the agentic workflow.
    Consumes LLMContext objects from llm_context_node outputs.

    Args:
        requirements_matcher_context: LLMContext for requirements matcher agent
        resume_evaluator_context: LLMContext for resume evaluator agent
        comms_drafter_context: LLMContext for communications drafter agent
        screening_result_schema_template: Schema template dictionary from YAML dataset

    Returns:
        Screening result as dictionary
    """
    # Create agents with tools
    requirements_matcher = create_requirements_matcher_agent_with_tools(
        requirements_matcher_context
    )
    resume_evaluator = create_resume_evaluator_agent_with_tools(
        resume_evaluator_context
    )
    comms_drafter = create_comms_drafter_agent_with_tools(
        comms_drafter_context
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
    email_task = create_email_draft_task(
        comms_drafter_context,
        comms_drafter,
    )

    # Create crew
    crew = Crew(
        agents=[requirements_matcher, resume_evaluator, comms_drafter],
        tasks=[requirements_task, evaluation_task, email_task],
        verbose=True,
    )

    # Execute crew with retry logic for connection errors
    crew_result = execute_crew_with_retry(crew)

    # Extract and structure result (raw, not validated)
    # Validation will be done in the reporting pipeline
    screening_result = extract_screening_result(crew_result)
    
    return screening_result
