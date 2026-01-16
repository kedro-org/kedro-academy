"""Kedro nodes for multi-agent AutoGen PPT generation pipeline.

This module contains node functions for agent orchestration only.
Deterministic preprocessing and postprocessing are handled separately.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from kedro.pipeline.llm_context import LLMContext

from .agent import (
    PlannerAgent,
    ChartGeneratorAgent,
    SummarizerAgent,
    CriticAgent,
)
from .utils import format_ma_prompts

logger = logging.getLogger(__name__)


def orchestrate_multi_agent_workflow(
    planner_context: LLMContext,
    chart_context: LLMContext,
    summarizer_context: LLMContext,
    critic_context: LLMContext,
    slide_configs: dict[str, Any],
    quality_assurance_params: dict[str, Any],
) -> dict[str, Any]:
    """Orchestrate multi-agent workflow to generate charts and summaries.

    This is the agentic node that coordinates multiple agents to generate content.
    Each agent receives only the fields relevant to its task.

    Args:
        planner_context: LLMContext for planner agent
        chart_context: LLMContext for chart generator agent
        summarizer_context: LLMContext for summarizer agent
        critic_context: LLMContext for critic agent
        slide_configs: Agent-specific slide views from preprocessing:
            - planner_slides: all fields
            - chart_slides: slide_title, chart_instruction, data_context
            - summarizer_slides: slide_title, summary_instruction, data_context
        quality_assurance_params: QA parameters for critic

    Returns:
        Dict containing slide content (chart_paths and summaries) for assembly
    """
    # Extract agent-specific slide views
    planner_slides = slide_configs.get('planner_slides', {})
    chart_slides = slide_configs.get('chart_slides', {})
    summarizer_slides = slide_configs.get('summarizer_slides', {})

    # Create agents directly from LLMContext
    planner_agent = PlannerAgent(planner_context).compile()
    chart_agent = ChartGeneratorAgent(chart_context).compile()
    summarizer_agent = SummarizerAgent(summarizer_context).compile()
    critic_agent = CriticAgent(critic_context).compile()

    # Format prompts using agent-specific views
    critic_user_prompt = critic_context.prompts.get("critic_user_prompt")
    planner_prompts, chart_prompts, summarizer_prompts = format_ma_prompts(
        planner_slides,
        chart_slides,
        summarizer_slides,
        planner_context.prompts.get("planner_user_prompt"),
        chart_context.prompts.get("chart_generator_user_prompt"),
        summarizer_context.prompts.get("summarizer_user_prompt"),
    )

    # Run multi-agent workflow (use planner_slides as main iterator since it has all fields)
    slide_content = {}

    for slide_key, planner_config in planner_slides.items():
        # Planner analyzes requirements
        asyncio.run(planner_agent.invoke(planner_prompts[slide_key]))

        # Chart generation
        chart_query = (
            f"{chart_prompts[slide_key]}\n\n"
            f"Task: Generate a chart using the generate_chart tool. "
            f"Provide the chart instruction and let the tool analyze the data and create the chart."
        )
        chart_output = asyncio.run(chart_agent.invoke(chart_query))
        chart_path = chart_output.chart_path if hasattr(chart_output, 'chart_path') else ""

        # Summary generation
        chart_status = f"Chart generated: {chart_path}" if chart_path else "Chart generation in progress"
        summary_query = (
            f"{summarizer_prompts[slide_key].replace('{chart_status}', chart_status)}\n\n"
            f"Task: Generate a summary using the generate_summary tool. "
            f"Provide the summary instruction and let the tool analyze the data and generate insights."
        )
        summary_output = asyncio.run(summarizer_agent.invoke(summary_query))
        summary_text = summary_output.summary_text if hasattr(summary_output, 'summary_text') else ""

        # Bundle content for assembly
        slide_content[slide_key] = {
            'slide_title': planner_config['slide_title'],
            'chart_path': chart_path,
            'summary': summary_text,
        }

        # QA review
        chart_available = 'Available' if chart_path and Path(chart_path).exists() else 'Not available'
        summary_preview = summary_text[:300] if summary_text else 'Not available'

        slide_content_str = (
            f"Slide Title: {planner_config['slide_title']}\n"
            f"Generated Chart: {chart_available}\n"
            f"Generated Summary: {summary_preview}"
        )
        expected_requirements = (
            f"Expected Slide Title: {planner_config['slide_title']}\n"
            f"Expected Chart Instruction: {planner_config.get('chart_instruction', '')}\n"
            f"Expected Summary Instruction: {planner_config.get('summary_instruction', '')}"
        )

        qa_query = critic_user_prompt.format(
            slide_content=slide_content_str,
            expected_requirements=expected_requirements,
            quality_standards=quality_assurance_params.get('quality_standards', ''),
            review_criteria=quality_assurance_params.get('review_criteria', '')
        )
        asyncio.run(critic_agent.invoke(qa_query))

    return {'slides': slide_content}
