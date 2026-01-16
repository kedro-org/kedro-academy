"""Single-agent PPT Generation using AutoGen."""
from __future__ import annotations

from typing import Any

from ppt_autogen_workflow.base import BaseAgent, ChartOutput, SummaryOutput


class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    """Agent for generating PowerPoint presentations from sales data."""

    agent_name = "PPTGenerator"
    system_prompt_key = "ppt_generator_system_prompt"

    async def invoke(self, task: str) -> dict[str, Any]:
        """Invoke the agent with a generic task."""
        self._ensure_compiled()
        result = await self._agent.run(task=task)
        return {"response": str(result.messages[-1].content) if result.messages else ""}

    async def invoke_for_chart(self, query: str) -> ChartOutput:
        """Invoke the agent to generate a chart."""
        return await self._run_with_output(query, ChartOutput)

    async def invoke_for_summary(self, query: str) -> SummaryOutput:
        """Invoke the agent to generate a summary."""
        return await self._run_with_output(query, SummaryOutput)
