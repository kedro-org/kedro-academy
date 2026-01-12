"""Kedro nodes for multi-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Any
from pathlib import Path

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import matplotlib.pyplot as plt

from autogen_ext.models.openai import OpenAIChatCompletionClient
from pptx import Presentation

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
from .tools import (
    build_planner_tools,
    build_chart_generator_tools,
    build_summarizer_tools,
    build_critic_tools,
)
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml
from ppt_autogen_workflow.utils.node_helpers import (
    format_summary_text,
    extract_chart_path,
    extract_summary_text,
    create_fallback_summary,
)

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
            chart_path, chart_fig = _generate_chart(
                compiled_chart_agent, chart_query, slide_key, chart_instruction
            )

            if chart_fig is not None:
                slide_charts_dict[slide_key] = chart_fig

            # Step 3: Summary generation
            chart_status = f"Chart generated: {chart_path}" if chart_path else "Chart generation in progress"
            summary_query = summarizer_formatted_prompts.get(slide_key, '').replace('{chart_status}', chart_status)
            summary_instruction = config.get('summary_instruction', '')
            summary_text = _generate_summary(
                compiled_summarizer_agent, summary_query, slide_key, summary_instruction
            )

            formatted_summary = format_summary_text(summary_text)
            slide_summaries_dict[slide_key] = formatted_summary

            # Step 4: QA review
            slide_title = config['slide_title']
            _run_qa_review(
                compiled_critic_agent, critic_user_prompt_template, quality_assurance_params,
                slide_title, chart_path, summary_text, config
            )

            # Step 5: Create slide
            slide_prs = _create_slide_presentation(
                slide_title, chart_path, formatted_summary, layout_params, styling_params
            )
            slide_presentations.append(slide_prs)

        final_presentation = combine_presentations(slide_presentations)
        return final_presentation, slide_charts_dict, slide_summaries_dict

    except Exception as e:
        logger.error(f"Multi-agent workflow failed: {str(e)}", exc_info=True)
        return _create_error_presentation(str(e)), {}, {}


def _generate_chart(
    chart_agent: ChartGeneratorAgent, query: str, slide_key: str, instruction: str
) -> tuple[str, plt.Figure | None]:
    """Generate chart using chart agent."""
    try:
        chart_result = asyncio.run(chart_agent.invoke(query))
        chart_path = extract_chart_path(chart_result)

        if chart_path and Path(chart_path).exists():
            try:
                from matplotlib.image import imread
                img = imread(chart_path)
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(img)
                ax.axis('off')
                return str(chart_path), fig
            except Exception as e:
                logger.warning(f"Could not load chart image: {e}")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{instruction[:50]}...",
                ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")

        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        return str(chart_path), fig

    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        return "", None


def _generate_summary(
    summarizer_agent: SummarizerAgent, query: str, slide_key: str, instruction: str
) -> str:
    """Generate summary using summarizer agent."""
    try:
        summary_result = asyncio.run(summarizer_agent.invoke(query))
        summary_text = extract_summary_text(summary_result)
        return summary_text if summary_text else create_fallback_summary(slide_key, instruction)
    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return create_fallback_summary(slide_key, instruction)


def _run_qa_review(
    critic_agent: CriticAgent, user_prompt_template: Any, qa_params: dict[str, Any],
    slide_title: str, chart_path: str | None, summary_text: str, config: dict[str, Any]
) -> dict[str, Any]:
    """Run QA review using critic agent."""
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
        return {"success": False, "error": str(e)}


def _create_slide_presentation(
    title: str, chart_path: str | None, summary: str,
    layout_params: dict[str, Any], styling_params: dict[str, Any]
) -> Presentation:
    """Create a single slide presentation."""
    chart = chart_path if chart_path and Path(chart_path).exists() else ""
    return create_slide(
        slide_title=title, chart_path=chart, summary_text=summary,
        layout_params=layout_params, styling_params=styling_params
    )


def _create_error_presentation(error_message: str) -> Presentation:
    """Create error presentation when workflow fails."""
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Multi-Agent Workflow Error"
    slide.placeholders[1].text = f"Error: {error_message}\nPlease check the logs for details."
    return prs
