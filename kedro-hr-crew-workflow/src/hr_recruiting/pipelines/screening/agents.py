"""Agent classes for screening pipeline.

This module contains all agent classes needed for the screening
orchestration workflow using CrewAI.
"""

from __future__ import annotations

from crewai import Agent
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.agent import BaseAgent



class RequirementsMatcherAgent(BaseAgent["RequirementsMatcherAgent"]):
    """Agent responsible for matching job requirements to candidate evidence.

    Usage:
        agent = RequirementsMatcherAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "RequirementsMatcherAgent"
    system_prompt_key = "requirements_matcher_agent_system_prompt"


class ResumeEvaluatorAgent(BaseAgent["ResumeEvaluatorAgent"]):
    """Agent responsible for evaluating candidate qualifications.

    Usage:
        agent = ResumeEvaluatorAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "ResumeEvaluatorAgent"
    system_prompt_key = "resume_evaluator_agent_system_prompt"


class CommsDrafterAgent(BaseAgent["CommsDrafterAgent"]):
    """Agent responsible for drafting professional email communications.

    Usage:
        agent = CommsDrafterAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "CommsDrafterAgent"
    system_prompt_key = "comms_drafter_agent_system_prompt"


def create_requirements_matcher_agent_with_tools(
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


def create_resume_evaluator_agent_with_tools(
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


def create_comms_drafter_agent_with_tools(
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
