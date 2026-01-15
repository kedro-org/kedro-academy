"""Single-agent PPT Generation using AutoGen."""
from __future__ import annotations

from ppt_autogen_workflow.base import BaseAgent, ChartOutput, SummaryOutput


class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    """Agent responsible for generating PowerPoint presentations from sales data.

    Usage:
        agent = PPTGenerationAgent(llm_context).compile()
        chart_output = await agent.invoke_for_chart(query)
    """

    agent_name = "PPTGenerator"
    system_prompt_key = "ppt_generator_system_prompt"

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
