"""Screening pipeline nodes - agentic processing with CrewAI."""

import json
import re
from typing import Any

from crewai import Agent, Crew, Task
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.models import ScreeningResult
from hr_recruiting.pipelines.screening.agents import (
    CommsDrafterAgent,
    RequirementsMatcherAgent,
    ResumeEvaluatorAgent,
)


def _get_screening_result_schema() -> str:
    """Generate JSON schema description for ScreeningResult format.

    Returns:
        Formatted string describing the expected ScreeningResult JSON schema
    """
    schema = ScreeningResult.model_json_schema()
    
    # Format schema as a readable description for LLM
    schema_description = f"""
The output must be a valid JSON object matching this ScreeningResult schema:
{json.dumps(schema, indent=2)}

Required fields:
- application_id (string): Application identifier
- match_score (float, 0-100): Overall match score
- must_have_coverage (float, 0-1): Must-have requirements coverage
- gaps (array of strings): Identified gaps
- strengths (array of strings): Candidate strengths
- risk_flags (array of strings): Risk flags
- recommendation (string): One of "proceed", "reject", or "review"
- email_draft (object or null): Email draft with subject, body, placeholders
- qa_suggestions (array of strings): QA suggestions
- match_results (array of objects): Each with requirement (string), snippet_ids (array), confidence (float 0-1)

Return ONLY valid JSON matching this schema, no additional text.
"""
    return schema_description.strip()


def _create_requirements_matcher_agent_with_tools(
    context: LLMContext,
) -> Agent:
    """Create requirements matcher agent with tools from context.

    Args:
        context: LLMContext containing LLM, prompts, and tools

    Returns:
        Configured Agent instance with tools
    """
    agent_wrapper = RequirementsMatcherAgent(context)
    agent_wrapper.compile()
    return agent_wrapper.agent


def _create_resume_evaluator_agent_with_tools(
    context: LLMContext,
) -> Agent:
    """Create resume evaluator agent with tools from context.

    Args:
        context: LLMContext containing LLM, prompts, and tools

    Returns:
        Configured Agent instance with tools
    """
    agent_wrapper = ResumeEvaluatorAgent(context)
    agent_wrapper.compile()
    return agent_wrapper.agent


def _create_comms_drafter_agent_with_tools(
    context: LLMContext,
) -> Agent:
    """Create communications drafter agent with tools from context.

    Args:
        context: LLMContext containing LLM, prompts, and tools

    Returns:
        Configured Agent instance with tools
    """
    agent_wrapper = CommsDrafterAgent(context)
    agent_wrapper.compile()
    return agent_wrapper.agent


def _create_requirements_matching_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create requirements matching task.

    Args:
        context: LLMContext containing prompts
        agent: Requirements matcher agent

    Returns:
        Configured Task instance
    """
    user_prompt = context.prompts.get("requirements_matching_user_prompt")
    description = str(user_prompt) if user_prompt else "Match job requirements to evidence snippets"

    return Task(
        description=description,
        agent=agent,
        expected_output="List of match results with requirement, snippet_ids, and confidence scores",
    )


def _create_resume_evaluation_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create resume evaluation task.

    Args:
        context: LLMContext containing prompts
        agent: Resume evaluator agent

    Returns:
        Configured Task instance
    """
    user_prompt = context.prompts.get("resume_evaluation_user_prompt")
    description = str(user_prompt) if user_prompt else "Evaluate candidate resume against job posting"
    
    # Include schema information in expected output
    schema_info = _get_screening_result_schema()
    expected_output = f"""Evaluation result as JSON matching ScreeningResult schema. 
Include: match_score (0-100), must_have_coverage (0-1), gaps[], strengths[], risk_flags[], recommendation (proceed/reject/review).
{schema_info}"""

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )


def _create_email_draft_task(
    context: LLMContext,
    agent: Agent,
) -> Task:
    """Create email draft task.

    Args:
        context: LLMContext containing prompts
        agent: Communications drafter agent

    Returns:
        Configured Task instance
    """
    user_prompt = context.prompts.get("email_draft_user_prompt")
    description = str(user_prompt) if user_prompt else "Draft email communication"
    
    # Include schema information for email draft format
    schema_info = _get_screening_result_schema()
    expected_output = f"""Complete ScreeningResult as JSON combining all previous task outputs.
Include email_draft with subject, body, and placeholders.
The final output should be a complete ScreeningResult JSON object.
{schema_info}"""

    return Task(
        description=description,
        agent=agent,
        expected_output=expected_output,
    )


def _create_screening_crew(
    requirements_matcher: Agent,
    resume_evaluator: Agent,
    comms_drafter: Agent,
    requirements_task: Task,
    evaluation_task: Task,
    email_task: Task,
) -> Crew:
    """Create CrewAI crew with agents and tasks.

    Args:
        requirements_matcher: Requirements matcher agent
        resume_evaluator: Resume evaluator agent
        comms_drafter: Communications drafter agent
        requirements_task: Requirements matching task
        evaluation_task: Resume evaluation task
        email_task: Email draft task

    Returns:
        Configured Crew instance
    """
    return Crew(
        agents=[requirements_matcher, resume_evaluator, comms_drafter],
        tasks=[requirements_task, evaluation_task, email_task],
        verbose=True,
    )


def _execute_crew(crew: Crew) -> Any:
    """Execute CrewAI crew and return result.

    Args:
        crew: Configured Crew instance

    Returns:
        Crew execution result
    """
    return crew.kickoff()


def _parse_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON object from text if present.

    Args:
        text: Text that may contain JSON

    Returns:
        Parsed JSON dictionary or None if not found
    """
    # Try to find JSON in the text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _extract_match_results(task_output: str) -> list[dict[str, Any]]:
    """Extract match results from requirements matching task output.

    Args:
        task_output: Output from requirements matching task

    Returns:
        List of match result dictionaries
    """
    match_results = []
    
    # Try to parse as JSON first
    parsed = _parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        if "match_results" in parsed:
            match_results = parsed["match_results"]
        elif isinstance(parsed, list):
            match_results = parsed
    
    # If no JSON found, try to extract from text format
    if not match_results:
        # Look for list-like patterns in text
        # This is a fallback - in production, agents should return structured JSON
        pass
    
    return match_results if match_results else []


def _extract_evaluation_data(task_output: str) -> dict[str, Any]:
    """Extract evaluation data from resume evaluation task output.

    Args:
        task_output: Output from resume evaluation task

    Returns:
        Dictionary with match_score, must_have_coverage, gaps, strengths, risk_flags, recommendation
    """
    evaluation_data = {
        "match_score": 0.0,
        "must_have_coverage": 0.0,
        "gaps": [],
        "strengths": [],
        "risk_flags": [],
        "recommendation": "review",
    }
    
    # Try to parse as JSON first
    parsed = _parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        evaluation_data.update({
            "match_score": float(parsed.get("match_score", 0.0)),
            "must_have_coverage": float(parsed.get("must_have_coverage", 0.0)),
            "gaps": parsed.get("gaps", []),
            "strengths": parsed.get("strengths", []),
            "risk_flags": parsed.get("risk_flags", []),
            "recommendation": parsed.get("recommendation", "review"),
        })
    else:
        # Fallback: try to extract from text using regex patterns
        # Extract match_score
        score_match = re.search(r'match_score[:\s]*(\d+\.?\d*)', task_output, re.IGNORECASE)
        if score_match:
            evaluation_data["match_score"] = float(score_match.group(1))
        
        # Extract recommendation
        rec_match = re.search(r'recommendation[:\s]*(proceed|reject|review)', task_output, re.IGNORECASE)
        if rec_match:
            evaluation_data["recommendation"] = rec_match.group(1).lower()
    
    return evaluation_data


def _extract_email_draft(task_output: str) -> dict[str, Any]:
    """Extract email draft from communications drafter task output.

    Args:
        task_output: Output from email draft task

    Returns:
        Dictionary with subject, body, and placeholders
    """
    email_draft = {
        "subject": "Application Update",
        "body": "",
        "placeholders": {},
    }
    
    # Try to parse as JSON first
    parsed = _parse_json_from_text(task_output)
    if parsed and isinstance(parsed, dict):
        email_draft.update({
            "subject": parsed.get("subject", "Application Update"),
            "body": parsed.get("body", ""),
            "placeholders": parsed.get("placeholders", {}),
        })
    else:
        # Fallback: try to extract from text
        # Extract subject
        subject_match = re.search(r'subject[:\s]*(.+?)(?:\n|$)', task_output, re.IGNORECASE | re.MULTILINE)
        if subject_match:
            email_draft["subject"] = subject_match.group(1).strip()
        
        # Extract body (everything after "body:" or main content)
        body_match = re.search(r'body[:\s]*(.+?)(?:\n\n|\Z)', task_output, re.IGNORECASE | re.DOTALL)
        if body_match:
            email_draft["body"] = body_match.group(1).strip()
        else:
            # If no explicit body marker, use the full output as body
            email_draft["body"] = task_output.strip()
    
    return email_draft


def _extract_screening_result(crew_result: Any) -> dict[str, Any]:
    """Extract and structure screening result from crew execution.

    Args:
        crew_result: Result from crew.kickoff()

    Returns:
        Structured screening result dictionary matching ScreeningResult schema
    """
    # Initialize default values
    screening_result = {
        "application_id": "unknown_unknown",
        "match_score": 0.0,
        "must_have_coverage": 0.0,
        "gaps": [],
        "strengths": [],
        "risk_flags": [],
        "recommendation": "review",
        "email_draft": None,
        "qa_suggestions": [],
        "match_results": [],
    }
    
    try:
        # CrewAI result structure: crew_result contains task outputs
        # Access task outputs - the structure may vary based on CrewAI version
        task_outputs = []
        
        # Try different ways to access task outputs
        if hasattr(crew_result, "tasks_output"):
            task_outputs = crew_result.tasks_output
        elif hasattr(crew_result, "tasks"):
            task_outputs = [task.output for task in crew_result.tasks if hasattr(task, "output")]
        elif isinstance(crew_result, list):
            task_outputs = crew_result
        elif isinstance(crew_result, str):
            # If result is a single string, treat it as the final task output
            task_outputs = [crew_result]
        
        # First, try to parse the final output as a complete ScreeningResult
        # (since we instructed the final task to output in ScreeningResult format)
        if task_outputs:
            final_output = str(task_outputs[-1]) if task_outputs else ""
            parsed_result = _parse_json_from_text(final_output)
            
            # If we got a complete ScreeningResult, validate and use it
            if parsed_result and isinstance(parsed_result, dict):
                try:
                    # Validate against ScreeningResult schema
                    validated = ScreeningResult(**parsed_result)
                    return validated.model_dump()
                except Exception:
                    # If validation fails, fall through to partial extraction
                    pass
        
        # Fallback: Process individual task outputs (assuming order: requirements, evaluation, email)
        if len(task_outputs) >= 1:
            # First task: requirements matching
            match_results = _extract_match_results(str(task_outputs[0]))
            screening_result["match_results"] = match_results
        
        if len(task_outputs) >= 2:
            # Second task: resume evaluation
            eval_data = _extract_evaluation_data(str(task_outputs[1]))
            screening_result.update(eval_data)
        
        if len(task_outputs) >= 3:
            # Third task: email draft (or complete ScreeningResult)
            final_output_str = str(task_outputs[2])
            parsed = _parse_json_from_text(final_output_str)
            
            if parsed and isinstance(parsed, dict):
                # Check if it's a complete ScreeningResult
                if "application_id" in parsed and "match_score" in parsed:
                    try:
                        validated = ScreeningResult(**parsed)
                        return validated.model_dump()
                    except Exception:
                        pass
                
                # Otherwise, extract just email_draft
                if "email_draft" in parsed:
                    screening_result["email_draft"] = parsed["email_draft"]
                else:
                    email_draft = _extract_email_draft(final_output_str)
                    screening_result["email_draft"] = email_draft
            else:
                email_draft = _extract_email_draft(final_output_str)
                screening_result["email_draft"] = email_draft
        
        # Generate application_id from available data if possible
        # This would ideally come from the evaluation task output
        if screening_result.get("match_results"):
            # Try to construct from match results context
            pass  # Would need additional context
        
    except Exception as e:
        # Log error but continue with defaults
        # In production, use proper logging
        print(f"Error parsing crew result: {e}")  # noqa: T201
    
    # Ensure all required fields have valid defaults
    if screening_result["email_draft"] is None:
        screening_result["email_draft"] = {
            "subject": "Application Update",
            "body": "Thank you for your application.",
            "placeholders": {},
        }
    
    return screening_result


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

    Returns:
        Screening result as dictionary
    """
    # Create agents with tools
    requirements_matcher = _create_requirements_matcher_agent_with_tools(
        requirements_matcher_context
    )
    resume_evaluator = _create_resume_evaluator_agent_with_tools(
        resume_evaluator_context
    )
    comms_drafter = _create_comms_drafter_agent_with_tools(
        comms_drafter_context
    )

    # Create tasks
    requirements_task = _create_requirements_matching_task(
        requirements_matcher_context,
        requirements_matcher,
    )
    evaluation_task = _create_resume_evaluation_task(
        resume_evaluator_context,
        resume_evaluator,
    )
    email_task = _create_email_draft_task(
        comms_drafter_context,
        comms_drafter,
    )

    # Create crew
    crew = _create_screening_crew(
        requirements_matcher,
        resume_evaluator,
        comms_drafter,
        requirements_task,
        evaluation_task,
        email_task,
    )

    # Execute crew
    crew_result = _execute_crew(crew)

    # Extract and structure result (raw, not validated)
    # Validation will be done in the reporting pipeline
    screening_result = _extract_screening_result(crew_result)
    
    return screening_result
