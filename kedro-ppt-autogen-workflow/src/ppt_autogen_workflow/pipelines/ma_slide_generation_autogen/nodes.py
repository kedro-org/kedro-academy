"""Kedro nodes for multi-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from pptx import Presentation

from autogen_ext.models.openai import OpenAIChatCompletionClient

from .agent_planner import PlannerAgent, create_planner_agent
from .agent_chart import ChartGeneratorAgent, create_chart_generator_agent, generate_chart
from .agent_summarizer import SummarizerAgent, create_summarizer_agent, generate_summary
from .agent_critic import CriticAgent, create_critic_agent, run_qa_review
from .tools import (
    build_planner_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)
from ppt_autogen_workflow.utils.ppt_builder import combine_presentations, create_slide
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml
from ppt_autogen_workflow.utils.node_helpers import format_summary_text

logger = logging.getLogger(__name__)


def init_tools(sales_data: pd.DataFrame) -> dict[str, Any]:
    """Initialize all tools needed for PPT generation agents."""
    return {
        "planner_tools": build_planner_tools(sales_data),
        "chart_generator_tools": build_chart_generator_tools(sales_data),
        "summarizer_tools": build_summarizer_tools(sales_data),
        "critic_tools": build_critic_tools(),
    }


def analyze_requirements(
    slide_generation_requirements: dict[str, Any],
    styling_params: dict[str, Any],
    layout_params: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Analyze requirements and create structured requirement objects for each agent type."""
    try:
        slide_definitions = parse_instructions_yaml(slide_generation_requirements)

        planner_requirement = {
            'slides': {},
            'styling': styling_params,
            'layout': layout_params,
        }
        chart_requirement = {'slides': {}}
        summarizer_requirement = {'slides': {}}

        data_context = "Sales data available through agent tools"

        for slide_key, slide_config in slide_definitions.items():
            objective = slide_config.get('objective', {})
            slide_title = objective.get('slide_title', slide_key)
            chart_instruction = objective.get('chart_instruction', '')
            summary_instruction = objective.get('summary_instruction', '')

            planner_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }

            chart_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'data_context': data_context,
            }

            summarizer_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }
        
        return (planner_requirement, chart_requirement, summarizer_requirement)

    except Exception as e:
        logger.error(f"Failed to analyze requirements: {str(e)}", exc_info=True)
        raise


def compile_planner_agent(
    planner_requirement: dict[str, Any],
    planner_system_prompt: Any,
    planner_user_prompt: Any,
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> PlannerAgent:
    """Compile the Planner Agent and format user prompts."""
    try:
        system_prompt_text = planner_system_prompt.format()
        planner_tools = tools["planner_tools"]
        agent = create_planner_agent(model_client, system_prompt_text, planner_tools)

        formatted_prompts = {}
        for slide_key, slide_config in planner_requirement['slides'].items():
            formatted_prompt = planner_user_prompt.format(
                slide_title=slide_config['slide_title'],
                chart_instruction=slide_config['chart_instruction'],
                summary_instruction=slide_config['summary_instruction'],
                data_context=slide_config['data_context']
            )
            formatted_prompts[slide_key] = formatted_prompt

        agent._formatted_prompts = formatted_prompts
        agent._planner_requirement = planner_requirement
        return agent
    except Exception as e:
        logger.error(f"Failed to compile planner agent: {str(e)}", exc_info=True)
        raise


def compile_chart_generator_agent(
    chart_requirement: dict[str, Any],
    chart_generator_system_prompt: Any,
    chart_generator_user_prompt: Any,
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> ChartGeneratorAgent:
    """Compile Chart Generator Agent and format user prompts."""
    try:
        system_prompt_text = chart_generator_system_prompt.format()
        chart_generator_tools = tools["chart_generator_tools"]
        agent = create_chart_generator_agent(model_client, system_prompt_text, chart_generator_tools)

        formatted_prompts = {}
        for slide_key, slide_config in chart_requirement['slides'].items():
            slide_title = slide_config['slide_title']
            chart_instruction = slide_config['chart_instruction']
            data_context = slide_config['data_context']

            chart_config = f"Slide Title: {slide_title}\nChart Instruction: {chart_instruction}\nData Context: {data_context}"
            formatted_prompt = chart_generator_user_prompt.format(chart_config=chart_config)
            formatted_prompts[slide_key] = formatted_prompt

        agent._formatted_prompts = formatted_prompts
        agent._chart_requirement = chart_requirement
        return agent

    except Exception as e:
        logger.error(f"Failed to compile chart generator agent: {str(e)}")
        raise


def compile_summarizer_agent(
    summarizer_requirement: dict[str, Any],
    summarizer_system_prompt: Any,
    summarizer_user_prompt: Any,
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> SummarizerAgent:
    """Compile Summarizer Agent and format user prompts."""
    try:
        system_prompt_text = summarizer_system_prompt.format()
        summarizer_tools = tools["summarizer_tools"]
        agent = create_summarizer_agent(model_client, system_prompt_text, summarizer_tools)

        formatted_prompts = {}
        for slide_key, slide_config in summarizer_requirement['slides'].items():
            summary_instruction = slide_config['summary_instruction']
            data_context = slide_config['data_context']

            summarizer_config = f"Summary Instruction: {summary_instruction}\nData Context: {data_context}"
            formatted_prompt = summarizer_user_prompt.format(
                summarizer_config=summarizer_config,
                chart_status="{chart_status}"
            )
            formatted_prompts[slide_key] = formatted_prompt

        agent._formatted_prompts = formatted_prompts
        agent._summarizer_requirement = summarizer_requirement
        agent._user_prompt_template = summarizer_user_prompt
        return agent

    except Exception as e:
        logger.error(f"Failed to compile summarizer agent: {str(e)}")
        raise


def compile_critic_agent(
    critic_system_prompt: Any,
    critic_user_prompt: Any,
    quality_assurance_params: dict[str, Any],
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> CriticAgent:
    """Compile Critic Agent for QA."""
    try:
        system_prompt_text = critic_system_prompt.format()
        critic_tools = tools["critic_tools"]
        agent = create_critic_agent(model_client, system_prompt_text, critic_tools)
        agent._user_prompt_template = critic_user_prompt
        agent._quality_assurance_params = quality_assurance_params
        return agent
    except Exception as e:
        logger.error(f"Failed to compile critic agent: {str(e)}")
        raise


def orchestrate_multi_agent_workflow(
    compiled_planner_agent: PlannerAgent,
    compiled_chart_agent: ChartGeneratorAgent,
    compiled_summarizer_agent: SummarizerAgent,
    compiled_critic_agent: CriticAgent,
) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    """Orchestrate multi-agent workflow to generate charts and summaries.

    This node focuses purely on agent orchestration. Slide assembly is handled
    by a separate deterministic node.

    Returns:
        Tuple of (slide_chart_paths, slide_summaries, slide_configs)
    """
    planner_requirement = compiled_planner_agent._planner_requirement
    planner_formatted_prompts = compiled_planner_agent._formatted_prompts
    chart_formatted_prompts = compiled_chart_agent._formatted_prompts
    summarizer_formatted_prompts = compiled_summarizer_agent._formatted_prompts
    critic_user_prompt_template = compiled_critic_agent._user_prompt_template
    quality_assurance_params = compiled_critic_agent._quality_assurance_params

    layout_params = planner_requirement.get('layout', {})
    styling_params = planner_requirement.get('styling', {})
    slide_configs = planner_requirement['slides']

    slide_chart_paths = {}
    slide_summaries = {}

    for slide_key, config in slide_configs.items():
        # Step 1: Planner analyzes the slide requirements
        planner_query = planner_formatted_prompts.get(slide_key, '')
        asyncio.run(compiled_planner_agent.invoke(planner_query))

        # Step 2: Chart generation
        chart_instruction = config.get('chart_instruction', '')
        chart_query = chart_formatted_prompts.get(slide_key, '')
        chart_path = generate_chart(
            compiled_chart_agent, chart_query, slide_key, chart_instruction
        )
        slide_chart_paths[slide_key] = chart_path

        # Step 3: Summary generation
        chart_status = f"Chart generated: {chart_path}" if chart_path else "Chart generation in progress"
        summary_query = summarizer_formatted_prompts.get(slide_key, '').replace('{chart_status}', chart_status)
        summary_instruction = config.get('summary_instruction', '')
        summary_text = generate_summary(
            compiled_summarizer_agent, summary_query, slide_key, summary_instruction
        )
        slide_summaries[slide_key] = format_summary_text(summary_text)

        # Step 4: QA review
        slide_title = config['slide_title']
        run_qa_review(
            compiled_critic_agent, critic_user_prompt_template, quality_assurance_params,
            slide_title, chart_path, summary_text, config
        )

    # Package configs with layout/styling for the assembly node
    assembly_configs = {
        'slides': slide_configs,
        'layout': layout_params,
        'styling': styling_params,
    }

    return slide_chart_paths, slide_summaries, assembly_configs


def assemble_presentation(
    slide_chart_paths: dict[str, str],
    slide_summaries: dict[str, str],
    slide_configs: dict[str, Any],
) -> Any:
    """Assemble final presentation from generated charts and summaries.

    This is a deterministic node that creates slides from the agent-generated content.

    Args:
        slide_chart_paths: Dict mapping slide_key to chart image path
        slide_summaries: Dict mapping slide_key to formatted summary text
        slide_configs: Dict containing slide metadata and layout/styling params

    Returns:
        Combined PowerPoint presentation
    """
    try:
        slides = slide_configs.get('slides', {})
        layout_params = slide_configs.get('layout', {})
        styling_params = slide_configs.get('styling', {})

        slide_presentations = []
        for slide_key, config in slides.items():
            slide_title = config['slide_title']
            chart_path = slide_chart_paths.get(slide_key, '')
            summary = slide_summaries.get(slide_key, '')

            chart = chart_path if chart_path and Path(chart_path).exists() else ""
            slide_prs = create_slide(
                slide_title=slide_title,
                chart_path=chart,
                summary_text=summary,
                layout_params=layout_params,
                styling_params=styling_params,
            )
            slide_presentations.append(slide_prs)

        return combine_presentations(slide_presentations)

    except Exception as e:
        logger.error(f"Presentation assembly failed: {str(e)}", exc_info=True)
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "Presentation Assembly Error"
        slide.placeholders[1].text = f"Error: {str(e)}"
        return prs
