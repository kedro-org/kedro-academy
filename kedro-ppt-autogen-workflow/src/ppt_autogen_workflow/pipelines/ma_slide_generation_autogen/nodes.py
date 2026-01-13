"""Kedro nodes for multi-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt

from autogen_ext.models.openai import OpenAIChatCompletionClient

from .agent import (
    create_planner_agent,
    create_chart_generator_agent,
    create_summarizer_agent,
    create_critic_agent,
    PlannerAgent,
    ChartGeneratorAgent,
    SummarizerAgent,
    CriticAgent
)
from .agent_helpers import (
    generate_chart,
    generate_summary,
    run_qa_review,
    create_slide_presentation,
    create_error_presentation,
)
from .tools import (
    build_planner_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)
from ppt_autogen_workflow.utils.ppt_builder import combine_presentations
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
) -> tuple[Any, dict[str, plt.Figure], dict[str, str]]:
    """Orchestrate multi-agent workflow in round-robin fashion."""
    try:
        planner_requirement = compiled_planner_agent._planner_requirement
        planner_formatted_prompts = compiled_planner_agent._formatted_prompts
        chart_formatted_prompts = compiled_chart_agent._formatted_prompts
        summarizer_formatted_prompts = compiled_summarizer_agent._formatted_prompts
        critic_user_prompt_template = compiled_critic_agent._user_prompt_template
        quality_assurance_params = compiled_critic_agent._quality_assurance_params

        layout_params = planner_requirement.get('layout', {})
        styling_params = planner_requirement.get('styling', {})
        slide_configs = planner_requirement['slides']

        slide_charts_dict = {}
        slide_summaries_dict = {}
        slide_presentations = []

        for slide_key, config in slide_configs.items():
            # Step 1: Planner analyzes the slide requirements
            planner_query = planner_formatted_prompts.get(slide_key, '')
            asyncio.run(compiled_planner_agent.invoke(planner_query))

            # Step 2: Chart generation
            chart_instruction = config.get('chart_instruction', '')
            chart_query = chart_formatted_prompts.get(slide_key, '')
            chart_path, chart_fig = generate_chart(
                compiled_chart_agent, chart_query, slide_key, chart_instruction
            )

            if chart_fig is not None:
                slide_charts_dict[slide_key] = chart_fig

            # Step 3: Summary generation
            chart_status = f"Chart generated: {chart_path}" if chart_path else "Chart generation in progress"
            summary_query = summarizer_formatted_prompts.get(slide_key, '').replace('{chart_status}', chart_status)
            summary_instruction = config.get('summary_instruction', '')
            summary_text = generate_summary(
                compiled_summarizer_agent, summary_query, slide_key, summary_instruction
            )

            formatted_summary = format_summary_text(summary_text)
            slide_summaries_dict[slide_key] = formatted_summary

            # Step 4: QA review
            slide_title = config['slide_title']
            run_qa_review(
                compiled_critic_agent, critic_user_prompt_template, quality_assurance_params,
                slide_title, chart_path, summary_text, config
            )

            # Step 5: Create slide
            slide_prs = create_slide_presentation(
                slide_title, chart_path, formatted_summary, layout_params, styling_params
            )
            slide_presentations.append(slide_prs)

        final_presentation = combine_presentations(slide_presentations)
        return final_presentation, slide_charts_dict, slide_summaries_dict

    except Exception as e:
        logger.error(f"Multi-agent workflow failed: {str(e)}", exc_info=True)
        return create_error_presentation(str(e)), {}, {}
