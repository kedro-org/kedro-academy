"""Kedro nodes for multi-agent AutoGen PPT generation pipeline.

This module contains node functions for agent orchestration only.
Deterministic preprocessing and postprocessing are handled separately.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from kedro.pipeline.llm_context import LLMContext

# Import agent classes and helpers
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
    ma_slide_configs: dict[str, Any],
    quality_assurance_params: dict[str, Any],
) -> dict[str, Any]:
    """Orchestrate multi-agent workflow to generate charts and summaries.

    This is the agentic node that coordinates multiple agents to generate content.
    Agents use thin tools that generate charts/summaries from pre-computed data.

    Args:
        planner_context: LLMContext for planner agent
        chart_context: LLMContext for chart generator agent
        summarizer_context: LLMContext for summarizer agent
        critic_context: LLMContext for critic agent
        ma_slide_configs: Pre-parsed slide configurations from preprocessing
        quality_assurance_params: QA parameters for critic

    Returns:
        Dict containing slide content (chart_paths and summaries) for assembly
    """
    # Extract parsed requirements
    planner_slides = ma_slide_configs.get('planner_slides', {})
    chart_slides = ma_slide_configs.get('chart_slides', {})
    summarizer_slides = ma_slide_configs.get('summarizer_slides', {})

    # Create agents directly from LLMContext
    planner_agent = PlannerAgent(planner_context).compile()
    chart_agent = ChartGeneratorAgent(chart_context).compile()
    summarizer_agent = SummarizerAgent(summarizer_context).compile()
    critic_agent = CriticAgent(critic_context).compile()

    # Format prompts
    critic_user_prompt = critic_context.prompts.get("critic_user_prompt")
    planner_prompts, chart_prompts, summarizer_prompts = format_ma_prompts(
        planner_slides, chart_slides, summarizer_slides,
        planner_context.prompts.get("planner_user_prompt"),
        chart_context.prompts.get("chart_generator_user_prompt"),
        summarizer_context.prompts.get("summarizer_user_prompt"),
    )

    # Run multi-agent workflow
    slide_content = {}

    for slide_key, config in planner_slides.items():
        # Planner analyzes requirements - agent uses analyze_data tool based on instructions
        asyncio.run(planner_agent.invoke(planner_prompts[slide_key]))

        # Chart generation - agent uses generate_chart tool with instruction
        # Agent analyzes instruction and generates chart from data
        chart_query = f"{chart_prompts[slide_key]}\n\nTask: Generate a chart using the generate_chart tool. Provide the chart instruction and let the tool analyze the data and create the chart."
        chart_output = asyncio.run(chart_agent.invoke(chart_query))
        chart_path = chart_output.chart_path if hasattr(chart_output, 'chart_path') else ""

        # Summary generation - agent uses generate_summary tool with instruction
        # Agent analyzes instruction and generates insights from data
        chart_status = f"Chart generated: {chart_path}" if chart_path else "Chart generation in progress"
        summary_query = f"{summarizer_prompts[slide_key].replace('{chart_status}', chart_status)}\n\nTask: Generate a summary using the generate_summary tool. Provide the summary instruction and let the tool analyze the data and generate insights."
        summary_output = asyncio.run(summarizer_agent.invoke(summary_query))
        summary_text = summary_output.summary_text if hasattr(summary_output, 'summary_text') else ""

        # Bundle content for assembly
        slide_content[slide_key] = {
            'slide_title': config['slide_title'],
            'chart_path': chart_path,
            'summary': summary_text,
        }

        # QA review - format query and invoke critic agent
        chart_available = 'Available' if chart_path and Path(chart_path).exists() else 'Not available'
        summary_preview = summary_text[:300] if summary_text else 'Not available'
        
        slide_content_str = f"Slide Title: {config['slide_title']}\nGenerated Chart: {chart_available}\nGenerated Summary: {summary_preview}"
        expected_requirements = f"Expected Slide Title: {config['slide_title']}\nExpected Chart Instruction: {config.get('chart_instruction', '')}\nExpected Summary Instruction: {config.get('summary_instruction', '')}"
        
        qa_query = critic_user_prompt.format(
            slide_content=slide_content_str,
            expected_requirements=expected_requirements,
            quality_standards=quality_assurance_params.get('quality_standards', ''),
            review_criteria=quality_assurance_params.get('review_criteria', '')
        )
        asyncio.run(critic_agent.invoke(qa_query))

    return {'slides': slide_content}
