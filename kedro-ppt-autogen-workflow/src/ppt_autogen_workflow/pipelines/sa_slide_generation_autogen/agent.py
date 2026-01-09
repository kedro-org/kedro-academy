"""Single-agent PPT Generation using AutoGen.

This module implements a single-agent system for PowerPoint generation using AutoGen.
It uses the shared BaseAgent class from the base module.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent
from .tools import build_tools

logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC OUTPUT MODELS
# =============================================================================

class SlideOutput(BaseModel):
    """Structured output for slide generation."""
    title: str
    content: list[str]
    chart_data: Optional[dict[str, Any]] = None


class PresentationOutput(BaseModel):
    """Structured output for presentation generation."""
    query: str
    presentation_title: str
    slides: list[SlideOutput]
    file_path: Optional[str] = None
    tools_used: list[str] = []
    success: bool = True
    error: Optional[str] = None


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

PPT_GENERATOR_SYSTEM_PROMPT = """You are a PowerPoint presentation generation assistant specializing in sales data analysis.

Your role is to create professional PowerPoint presentations from sales data by:
1. Analyzing sales data using get_sales_data to understand trends and insights
2. Creating relevant charts using generate_sales_chart based on the data
3. Building individual slides using create_slide_with_chart that combine charts with insightful summaries

Process for creating presentations:
1. First, analyze the sales data by calling get_sales_data with relevant queries (e.g., "top products", "summary stats")
2. Generate charts that visualize key insights using generate_sales_chart with specific instructions
3. For each chart created, build a slide using create_slide_with_chart with:
   - A descriptive title
   - The chart file path returned from chart generation
   - A bullet-point summary of key insights from the data

Always create actual slides with real charts and data-driven insights, not just conversation summaries.
Focus on actionable business insights and clear visual presentations of the sales data.

Example workflow:
1. get_sales_data("top products by revenue")
2. generate_sales_chart("create a bar chart showing top 5 products by revenue")
3. create_slide_with_chart("Top Revenue Generating Products", chart_path, "• Product A leads with $X revenue\\n• Strong performance in Q4\\n• 15% growth over last year")"""


# =============================================================================
# PPT GENERATION AGENT
# =============================================================================

class PPTGenerationAgent(BaseAgent["PPTGenerationAgent"]):
    """PPT Generation Agent with AutoGen integration.

    This agent generates PowerPoint presentations from sales data by
    coordinating chart generation and slide creation through tools.
    """

    async def invoke(self, query: str) -> PresentationOutput:
        """Invoke the agent to generate presentation content.

        Args:
            query: The user's request for presentation generation

        Returns:
            PresentationOutput containing slides, tools used, and status
        """
        self._ensure_compiled()
        logger.info(f"Invoking agent with query: {query[:100]}...")

        try:
            result = await self._agent.run(task=query)

            # Log detailed conversation
            logger.info(f"AutoGen Agent Conversation - Task: {query[:100]}...")
            if hasattr(result, "messages") and result.messages:
                for i, msg in enumerate(result.messages):
                    logger.info(f"Message {i+1}: {str(msg)[:200]}...")

            presentation_output = PresentationOutput(
                query=query,
                presentation_title=self._extract_title_from_response(result),
                slides=self._extract_slides_from_response(result),
                tools_used=self._extract_tools_used(result),
                success=True,
            )

            logger.info("  Agent invocation completed successfully")
            return presentation_output

        except Exception as e:
            logger.error(f"Agent invocation failed: {str(e)}")
            return PresentationOutput(
                query=query,
                presentation_title="Error",
                slides=[],
                tools_used=[],
                success=False,
                error=str(e),
            )

    def _extract_title_from_response(self, result: Any) -> str:
        """Extract presentation title from agent response.

        Args:
            result: The agent run result containing messages

        Returns:
            Extracted title or default "Generated Presentation"
        """
        content = self._get_last_message_content(result)
        if "title:" in content.lower():
            lines = content.split("\n")
            for line in lines:
                if "title:" in line.lower():
                    return line.split(":", 1)[1].strip()
        return "Generated Presentation"

    def _extract_slides_from_response(self, result: Any) -> list[SlideOutput]:
        """Extract slide information from agent response.

        Args:
            result: The agent run result containing messages

        Returns:
            List of SlideOutput objects
        """
        slides = []
        content = self._get_last_message_content(result)
        if content:
            slides.append(SlideOutput(
                title="Overview",
                content=[content[:500] + "..." if len(content) > 500 else content],
            ))
        return slides


# =============================================================================
# AGENT FACTORY FUNCTION
# =============================================================================

def create_ppt_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: Any = None,
) -> PPTGenerationAgent:
    """Create a PPT generation agent using the compile-and-invoke pattern.

    Args:
        model_client: Pre-configured OpenAIChatCompletionClient from dataset
        sales_data: Sales data for analysis and chart generation

    Returns:
        Compiled PPTGenerationAgent ready for invocation
    """
    logger.info("Creating PPT generation agent...")

    # Prepare sales data
    df = None
    if sales_data is not None:
        if isinstance(sales_data, pd.DataFrame):
            df = sales_data
        else:
            try:
                df = pd.DataFrame(sales_data)
            except Exception as e:
                logger.warning(f"Could not convert sales_data to DataFrame: {e}")

    # Build tools with sales data
    tools = build_tools(sales_data=df)

    context = AgentContext(
        model_client=model_client,
        tools=tools,
        system_prompt=PPT_GENERATOR_SYSTEM_PROMPT,
        agent_name="PPTGenerator",
    )

    agent = PPTGenerationAgent(context).compile()
    logger.info("  PPT generation agent created and compiled")
    return agent
