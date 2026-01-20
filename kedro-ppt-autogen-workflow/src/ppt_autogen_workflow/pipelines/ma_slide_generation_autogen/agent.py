"""Agent classes for multi-agent AutoGen pipeline.

This module contains all agent classes needed for the multi-agent
orchestration workflow.
"""
from __future__ import annotations

from ppt_autogen_workflow.base import (
    BaseAgent,
    ChartOutput,
    PlanOutput,
    QAFeedbackOutput,
    SummaryOutput,
)


class PlannerAgent(BaseAgent["PlannerAgent"]):
    """Agent responsible for orchestrating and planning the agentic flow.

    Usage:
        agent = PlannerAgent(llm_context).compile()
        output = await agent.invoke(query)
    """

    agent_name = "PlannerAgent"
    system_prompt_key = "planner_system_prompt"

    async def invoke(self, query: str) -> PlanOutput:
        """Invoke the planner agent to create presentation plan.

        Returns:
            PlanOutput with plan and status
        """
        return await self._run_with_output(query, PlanOutput)


class ChartGeneratorAgent(BaseAgent["ChartGeneratorAgent"]):
    """Agent responsible for generating data visualizations.

    Usage:
        agent = ChartGeneratorAgent(llm_context).compile()
        output = await agent.invoke(chart_requirements)
    """

    agent_name = "ChartGeneratorAgent"
    system_prompt_key = "chart_generator_system_prompt"

    async def invoke(self, chart_requirements: str) -> ChartOutput:
        """Invoke the chart generator agent to create charts.

        Returns:
            ChartOutput with chart_path and status
        """
        return await self._run_with_output(chart_requirements, ChartOutput)


class SummarizerAgent(BaseAgent["SummarizerAgent"]):
    """Agent responsible for generating slide summaries.

    Usage:
        agent = SummarizerAgent(llm_context).compile()
        output = await agent.invoke(content_to_summarize)
    """

    agent_name = "SummarizerAgent"
    system_prompt_key = "summarizer_system_prompt"

    async def invoke(self, content_to_summarize: str) -> SummaryOutput:
        """Invoke the summarizer agent to create slide summaries.

        Returns:
            SummaryOutput with summary_text and status
        """
        return await self._run_with_output(content_to_summarize, SummaryOutput)


class CriticAgent(BaseAgent["CriticAgent"]):
    """Agent responsible for QA and feedback on slides.

    Usage:
        agent = CriticAgent(llm_context).compile()
        output = await agent.invoke(slide_content)
    """

    agent_name = "CriticAgent"
    system_prompt_key = "critic_system_prompt"

    async def invoke(self, slide_content: str) -> QAFeedbackOutput:
        """Invoke the critic agent to review and provide feedback on slides.

        Returns:
            QAFeedbackOutput with feedback, overall_score, and status
        """
        return await self._run_with_output(slide_content, QAFeedbackOutput)
