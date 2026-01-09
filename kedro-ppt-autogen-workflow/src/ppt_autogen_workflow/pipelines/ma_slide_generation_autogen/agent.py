"""Multi-agent PPT Generation using AutoGen.

This module implements a multi-agent system for PowerPoint generation using AutoGen.
It uses the shared BaseAgent class to eliminate code duplication across specialized agents.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent
from .tools import (
    build_planner_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)

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
        logger.info(f"Planner agent planning for query: {query[:100]}...")

        try:
            result = await self._agent.run(task=query)

            plan_output = {
                "query": query,
                "plan": self._extract_content_from_response(result, "plan"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            logger.info("  Planner agent completed successfully")
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
        logger.info("Chart generator agent creating charts...")

        try:
            result = await self._agent.run(task=chart_requirements)

            chart_output = {
                "requirements": chart_requirements,
                "chart_data": self._extract_content_from_response(result, "chart"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            logger.info("  Chart generator agent completed successfully")
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
        logger.info("Summarizer agent creating summaries...")

        try:
            result = await self._agent.run(task=content_to_summarize)

            summary_output = {
                "original_content": content_to_summarize,
                "summary": self._extract_content_from_response(result, "summary"),
                "tools_used": self._extract_tools_used(result),
                "success": True,
            }

            logger.info("  Summarizer agent completed successfully")
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
        logger.info("Critic agent reviewing slide content...")

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

            logger.info("  Critic agent completed review successfully")
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

# System prompts for each agent type
PLANNER_SYSTEM_PROMPT = """You are a presentation planning specialist.

Your role is to:
1. Analyze user requirements for presentations
2. Plan the structure and flow of slides
3. Determine what content and charts are needed
4. Coordinate with other agents (ChartGenerator, Summarizer, Critic)

When planning presentations:
- Break down user requirements into actionable tasks
- Design logical slide flow and structure
- Identify data visualization needs
- Plan content organization for maximum impact

Always provide detailed, structured plans with clear next steps for other agents."""

CHART_GENERATOR_SYSTEM_PROMPT = """You are a data visualization expert.

Your role is to:
1. Generate appropriate charts based on data and requirements
2. Validate chart designs for clarity and accuracy
3. Analyze data to recommend best visualization types
4. Ensure charts meet presentation standards

When creating charts:
- Select the most effective chart type for the data
- Ensure proper labeling and formatting
- Validate data accuracy and representation
- Provide recommendations for improvements

Focus on creating clear, impactful visualizations that enhance understanding."""

SUMMARIZER_SYSTEM_PROMPT = """You are a content summarization expert.

Your role is to:
1. Extract key points from detailed content
2. Create concise, impactful slide summaries
3. Generate appropriately formatted slide text
4. Ensure content is presentation-ready

When summarizing content:
- Focus on the most important and relevant points
- Use clear, concise language suitable for slides
- Structure content for visual presentation
- Maintain accuracy while improving readability

Create summaries that inform and engage audiences effectively."""

CRITIC_SYSTEM_PROMPT = """You are a presentation quality assurance expert.

Your role is to:
1. Assess slide quality against professional standards
2. Provide actionable feedback for improvements
3. Validate content accuracy and completeness
4. Ensure slides meet presentation best practices

When reviewing slides:
- Evaluate clarity, completeness, and visual appeal
- Check for accuracy and consistency
- Provide specific, actionable recommendations
- Score quality objectively using defined criteria

Give constructive feedback that helps create professional, effective presentations."""


def create_planner_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame | None = None,
) -> PlannerAgent:
    """Create a planner agent for orchestrating presentation workflow.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled PlannerAgent ready for invocation
    """
    logger.info("Creating planner agent...")

    context = AgentContext(
        model_client=model_client,
        tools=build_planner_tools(sales_data),
        system_prompt=PLANNER_SYSTEM_PROMPT,
        agent_name="PlannerAgent",
    )

    agent = PlannerAgent(context).compile()
    logger.info("  Planner agent created and compiled")
    return agent


def create_chart_generator_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame | None = None,
) -> ChartGeneratorAgent:
    """Create a chart generator agent for data visualization.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled ChartGeneratorAgent ready for invocation
    """
    logger.info("Creating chart generator agent...")

    context = AgentContext(
        model_client=model_client,
        tools=build_chart_generator_tools(sales_data),
        system_prompt=CHART_GENERATOR_SYSTEM_PROMPT,
        agent_name="ChartGeneratorAgent",
    )

    agent = ChartGeneratorAgent(context).compile()
    logger.info("  Chart generator agent created and compiled")
    return agent


def create_summarizer_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame | None = None,
) -> SummarizerAgent:
    """Create a summarizer agent for slide content creation.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled SummarizerAgent ready for invocation
    """
    logger.info("Creating summarizer agent...")

    context = AgentContext(
        model_client=model_client,
        tools=build_summarizer_tools(sales_data),
        system_prompt=SUMMARIZER_SYSTEM_PROMPT,
        agent_name="SummarizerAgent",
    )

    agent = SummarizerAgent(context).compile()
    logger.info("  Summarizer agent created and compiled")
    return agent


def create_critic_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame | None = None,
) -> CriticAgent:
    """Create a critic agent for slide quality assurance.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access (not used but kept for consistency)

    Returns:
        Compiled CriticAgent ready for invocation
    """
    logger.info("Creating critic agent...")

    context = AgentContext(
        model_client=model_client,
        tools=build_critic_tools(),
        system_prompt=CRITIC_SYSTEM_PROMPT,
        agent_name="CriticAgent",
    )

    agent = CriticAgent(context).compile()
    logger.info("  Critic agent created and compiled")
    return agent
