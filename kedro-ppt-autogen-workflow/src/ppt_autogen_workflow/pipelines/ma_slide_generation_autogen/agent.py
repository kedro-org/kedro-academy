"""Multi-agent PPT Generation using AutoGen."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow."""

    async def invoke(self, query: str) -> dict[str, Any]:
        """Invoke the planner agent to create presentation plan."""
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
    """Agent responsible for generating data visualizations."""

    async def invoke(self, chart_requirements: str) -> dict[str, Any]:
        """Invoke the chart generator agent to create charts."""
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
    """Agent responsible for generating slide summaries."""

    async def invoke(self, content_to_summarize: str) -> dict[str, Any]:
        """Invoke the summarizer agent to create slide summaries."""
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
    """Agent responsible for QA and feedback on slides."""

    async def invoke(self, slide_content: str) -> dict[str, Any]:
        """Invoke the critic agent to review and provide feedback on slides."""
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
        """Extract quality score from feedback dictionary."""
        if isinstance(feedback, dict) and "overall_score" in feedback:
            try:
                return float(feedback["overall_score"])
            except (ValueError, TypeError):
                pass
        return 8.0


def create_planner_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> PlannerAgent:
    """Create a planner agent for orchestrating presentation workflow."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="PlannerAgent",
    )
    return PlannerAgent(context).compile()


def create_chart_generator_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> ChartGeneratorAgent:
    """Create a chart generator agent for data visualization."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="ChartGeneratorAgent",
    )
    return ChartGeneratorAgent(context).compile()


def create_summarizer_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> SummarizerAgent:
    """Create a summarizer agent for slide content creation."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="SummarizerAgent",
    )
    return SummarizerAgent(context).compile()


def create_critic_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> CriticAgent:
    """Create a critic agent for slide quality assurance."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="CriticAgent",
    )
    return CriticAgent(context).compile()
