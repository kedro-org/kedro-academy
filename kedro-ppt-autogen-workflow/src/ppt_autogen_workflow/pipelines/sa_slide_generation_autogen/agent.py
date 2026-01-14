"""Single-agent PPT Generation using AutoGen."""
from __future__ import annotations

import logging

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent, ChartOutput, SummaryOutput

logger = logging.getLogger(__name__)


class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    """Agent responsible for generating PowerPoint presentations from sales data."""

    async def invoke_for_chart(self, query: str) -> ChartOutput:
        """Invoke the agent to generate a chart.

        Returns:
            ChartOutput with chart_path and status
        """
        return await self._run_with_output(query, ChartOutput)

    async def invoke_for_summary(self, query: str) -> SummaryOutput:
        """Invoke the agent to generate a summary.

        Returns:
            SummaryOutput with summary_text and status
        """
        return await self._run_with_output(query, SummaryOutput)

    async def invoke(self, query: str) -> ChartOutput:
        """Default invoke returns ChartOutput for backwards compatibility."""
        return await self.invoke_for_chart(query)


def create_ppt_agent(
    model_client: OpenAIChatCompletionClient,
    system_prompt: str,
    tools: list,
) -> PPTGenerationAgent:
    """Create a PPT generation agent."""
    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=system_prompt,
        agent_name="PPTGenerator",
    )
    return PPTGenerationAgent(context).compile()
