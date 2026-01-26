"""Agent classes for applications pipeline.

This module contains all agent classes needed for resume parsing
and normalization using CrewAI.
"""

from __future__ import annotations

from crewai import Agent
from kedro.pipeline.llm_context import LLMContext

from hr_recruiting.base.agent import BaseAgent


class ResumeParserAgent(BaseAgent["ResumeParserAgent"]):
    """Agent responsible for parsing and normalizing resume data.

    This agent handles the complex task of extracting structured information
    from resumes in various formats and styles. It can handle different
    resume layouts, section names, and formatting conventions.

    Usage:
        agent = ResumeParserAgent(llm_context).compile()
        # Agent is used within CrewAI tasks, not directly invoked
    """

    agent_name = "ResumeParserAgent"
    system_prompt_key = "resume_parser_agent_system_prompt"


def create_resume_parser_agent_with_tools(
    context: LLMContext,
) -> Agent:
    """Create ResumeParserAgent with tools from context.

    Args:
        context: LLMContext containing LLM, prompts, and tools

    Returns:
        Compiled CrewAI Agent
    """
    agent = ResumeParserAgent(context).compile()
    return agent.agent
