"""Multi-agent PPT Generation using AutoGen.

This module implements a multi-agent system for PowerPoint generation using AutoGen.
It uses the shared BaseAgent class and external prompt datasets following kedro best practices.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow.

    The PlannerAgent analyzes requirements and creates execution plans
    for presentation generation, coordinating with other specialized agents.
    """

    async def invoke(self, query: str) -> dict[str, Any]:
        """Invoke the planner agent to create presentation plan.

        Args:
            query: The planning query with slide requirements

        Returns:
            Dictionary containing:
            - query: Original query
            - plan: Extracted plan data
            - tools_used: List of tools invoked
            - success: Boolean indicating success
            - error: Error message if failed (optional)
        """
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=query)

            plan_output = {
                "query": query,
                "plan": self._extract_content_from_response(result, "plan"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            return plan_output

        except Exception as e:
            logger.error(f"Planner agent failed: {str(e)}")
            return {
                "query": query,
                "plan": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


class ChartGeneratorAgent(BaseAgent["ChartGeneratorAgent"]):
    """Agent responsible for generating data visualizations.

    The ChartGeneratorAgent creates charts based on data requirements
    and visualization best practices.
    """

    async def invoke(self, chart_requirements: str) -> dict[str, Any]:
        """Invoke the chart generator agent to create charts.

        Args:
            chart_requirements: Requirements for chart generation

        Returns:
            Dictionary containing:
            - requirements: Original requirements
            - chart_data: Extracted chart information
            - tools_used: List of tools invoked
            - success: Boolean indicating success
            - error: Error message if failed (optional)
        """
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=chart_requirements)

            chart_output = {
                "requirements": chart_requirements,
                "chart_data": self._extract_content_from_response(result, "chart"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            return chart_output

        except Exception as e:
            logger.error(f"Chart generator agent failed: {str(e)}")
            return {
                "requirements": chart_requirements,
                "chart_data": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


class SummarizerAgent(BaseAgent["SummarizerAgent"]):
    """Agent responsible for generating slide summaries.

    The SummarizerAgent extracts key points and creates concise,
    presentation-ready content summaries.
    """

    async def invoke(self, content_to_summarize: str) -> dict[str, Any]:
        """Invoke the summarizer agent to create slide summaries.

        Args:
            content_to_summarize: Content that needs to be summarized

        Returns:
            Dictionary containing:
            - original_content: Input content
            - summary: Extracted summary data
            - tools_used: List of tools invoked
            - success: Boolean indicating success
            - error: Error message if failed (optional)
        """
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=content_to_summarize)

            summary_output = {
                "original_content": content_to_summarize,
                "summary": self._extract_content_from_response(result, "summary"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            return summary_output

        except Exception as e:
            logger.error(f"Summarizer agent failed: {str(e)}")
            return {
                "original_content": content_to_summarize,
                "summary": {},
                "tools_used": [],
                "success": False,
                "error": str(e),
            }


class CriticAgent(BaseAgent["CriticAgent"]):
    """Agent responsible for QA and feedback on slides.

    The CriticAgent reviews generated content, provides quality scores,
    and offers actionable feedback for improvements.
    """

    async def invoke(self, slide_content: str) -> dict[str, Any]:
        """Invoke the critic agent to review and provide feedback on slides.

        Args:
            slide_content: The slide content to review

        Returns:
            Dictionary containing:
            - reviewed_content: Input content
            - feedback: Extracted feedback data
            - quality_score: Numeric quality score (0-10)
            - tools_used: List of tools invoked
            - success: Boolean indicating success
            - error: Error message if failed (optional)
        """
        self._ensure_compiled()

        try:
            result = await self._agent.run(task=slide_content)

            feedback = self._extract_content_from_response(result, "feedback")

            critic_output = {
                "reviewed_content": slide_content,
                "feedback": feedback,
                "quality_score": self._extract_quality_score(feedback),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            return critic_output

        except Exception as e:
            logger.error(f"Critic agent failed: {str(e)}")
            return {
                "reviewed_content": slide_content,
                "feedback": {},
                "quality_score": 0.0,
                "tools_used": [],
                "success": False,
                "error": str(e),
            }

    def _extract_quality_score(self, feedback: dict[str, Any]) -> float:
        """Extract quality score from feedback dictionary.

        Args:
            feedback: Dictionary containing feedback data

        Returns:
            Quality score as float, defaults to 8.0 if not found
        """
        if isinstance(feedback, dict) and "overall_score" in feedback:
            try:
                return float(feedback["overall_score"])
            except (ValueError, TypeError):
                pass
        return 8.0  # Default score


# =============================================================================
# AGENT FACTORY FUNCTIONS
# =============================================================================


def create_planner_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> PlannerAgent:
    """Create a planner agent for orchestrating presentation workflow.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        system_prompt: System prompt from prompt dataset
        tools: Pre-built tools for the agent

    Returns:
        Compiled PlannerAgent ready for invocation
    """
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="PlannerAgent",
    )

    agent = PlannerAgent(context).compile()
    return agent


def create_chart_generator_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> ChartGeneratorAgent:
    """Create a chart generator agent for data visualization.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        system_prompt: System prompt from prompt dataset
        tools: Pre-built tools for the agent

    Returns:
        Compiled ChartGeneratorAgent ready for invocation
    """
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="ChartGeneratorAgent",
    )

    agent = ChartGeneratorAgent(context).compile()
    return agent


def create_summarizer_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> SummarizerAgent:
    """Create a summarizer agent for slide content creation.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        system_prompt: System prompt from prompt dataset
        tools: Pre-built tools for the agent

    Returns:
        Compiled SummarizerAgent ready for invocation
    """
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="SummarizerAgent",
    )

    agent = SummarizerAgent(context).compile()
    return agent


def create_critic_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> CriticAgent:
    """Create a critic agent for slide quality assurance.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        system_prompt: System prompt from prompt dataset
        tools: Pre-built tools for the agent

    Returns:
        Compiled CriticAgent ready for invocation
    """
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="CriticAgent",
    )

    agent = CriticAgent(context).compile()
    return agent
