"""Critic Agent for multi-agent PPT generation pipeline.

This module contains the CriticAgent class and related helper
functions for QA and feedback on slides.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from autogen_ext.models.openai import OpenAIChatCompletionClient

from ppt_autogen_workflow.base import AgentContext, BaseAgent, QAFeedbackOutput

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent["CriticAgent"]):
    """Agent responsible for QA and feedback on slides."""

    async def invoke(self, slide_content: str) -> QAFeedbackOutput:
        """Invoke the critic agent to review and provide feedback on slides.

        Returns:
            QAFeedbackOutput with feedback, overall_score, and status
        """
        return await self._run_with_output(slide_content, QAFeedbackOutput)


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


def run_qa_review(
    critic_agent: CriticAgent, user_prompt_template: Any, qa_params: dict[str, Any],
    slide_title: str, chart_path: str | None, summary_text: str, config: dict[str, Any]
) -> QAFeedbackOutput:
    """Run QA review using critic agent with structured output.

    Args:
        critic_agent: Compiled critic agent
        user_prompt_template: Template for QA prompt
        qa_params: Quality assurance parameters
        slide_title: Title of the slide being reviewed
        chart_path: Path to generated chart
        summary_text: Generated summary text
        config: Slide configuration

    Returns:
        QAFeedbackOutput with feedback and quality score
    """
    try:
        chart_available = 'Available' if chart_path and Path(chart_path).exists() else 'Not available'
        summary_preview = summary_text[:300] if summary_text else 'Not available'

        slide_content = f"Slide Title: {slide_title}\nGenerated Chart: {chart_available}\nGenerated Summary: {summary_preview}"
        expected_requirements = f"Expected Slide Title: {slide_title}\nExpected Chart Instruction: {config.get('chart_instruction', '')}\nExpected Summary Instruction: {config.get('summary_instruction', '')}"

        qa_query = user_prompt_template.format(
            slide_content=slide_content,
            expected_requirements=expected_requirements,
            quality_standards=qa_params.get('quality_standards', ''),
            review_criteria=qa_params.get('review_criteria', '')
        )
        return asyncio.run(critic_agent.invoke(qa_query))

    except Exception as e:
        logger.error(f"Error in QA review: {str(e)}")
        return QAFeedbackOutput(feedback=f"Error: {str(e)}", overall_score=0.0, status="error")
