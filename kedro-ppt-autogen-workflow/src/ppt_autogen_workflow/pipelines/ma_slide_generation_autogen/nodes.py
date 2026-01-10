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
from ppt_autogen_workflow.utils.chart_generator import generate_chart
from ppt_autogen_workflow.utils.summary_generator import generate_summary
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

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
    planner_system_prompt: Any,
    planner_requirement: dict[str, Any],
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> PlannerAgent:
    """Compile the Planner Agent."""
    try:
        planner_tools = tools["planner_tools"]
        system_prompt_text = planner_system_prompt.format()
        agent = create_planner_agent(model_client, system_prompt_text, planner_tools)
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
    """Compile Chart Generator Agent and format user prompts using chart requirements."""
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
    """Compile Summarizer Agent and format user prompts using summarizer requirements."""
    try:
        system_prompt_text = summarizer_system_prompt.format()
        summarizer_tools = tools["summarizer_tools"]
        agent = create_summarizer_agent(model_client, system_prompt_text, summarizer_tools)
        
        formatted_prompts = {}
        for slide_key, slide_config in summarizer_requirement['slides'].items():
            slide_title = slide_config['slide_title']
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
    """Compile Critic Agent and prepare for prompt formatting."""
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
        chart_formatted_prompts = compiled_chart_agent._formatted_prompts
        chart_requirement = compiled_chart_agent._chart_requirement
        summarizer_formatted_prompts = compiled_summarizer_agent._formatted_prompts
        summarizer_user_prompt_template = compiled_summarizer_agent._user_prompt_template
        critic_user_prompt_template = compiled_critic_agent._user_prompt_template
        quality_assurance_params = compiled_critic_agent._quality_assurance_params
        
        layout_params = planner_requirement.get('layout', {})
        styling_params = planner_requirement.get('styling', {})
        slide_configs = planner_requirement['slides']

        slide_charts_dict = {}
        slide_summaries_dict = {}
        slide_presentations = []
        slide_qa_results = {}

        for slide_key, config in slide_configs.items():
            chart_instruction = config.get('chart_instruction', '')
            chart_query = chart_formatted_prompts.get(slide_key, '')
            
            chart_path, chart_fig = _generate_chart_for_slide_with_logging(
                chart_instruction, slide_key, compiled_chart_agent, chart_query
            )
            
            if chart_fig is not None:
                slide_charts_dict[slide_key] = chart_fig
            
            chart_status = f"Chart has been generated: {chart_path if chart_path else 'Chart generation in progress'}"
            summary_query = summarizer_formatted_prompts.get(slide_key, '').replace('{chart_status}', chart_status)
            summary_instruction = config.get('summary_instruction', '')
            
            summary_text = _generate_summary_for_slide_with_logging(
                summary_instruction, slide_key, compiled_summarizer_agent, summary_query
            )
            
            formatted_summary = _format_summary_text(summary_text)
            slide_summaries_dict[slide_key] = formatted_summary
            
            slide_title = config['slide_title']
            expected_chart_instruction = config.get('chart_instruction', '')
            expected_summary_instruction = config.get('summary_instruction', '')
            
            chart_available = 'Available' if chart_path and Path(chart_path).exists() else 'Not available'
            summary_preview = summary_text[:300] if summary_text else 'Not available'
            
            slide_content = f"""Slide Title: {slide_title}
Generated Chart: {chart_available}
Generated Summary: {summary_preview}"""
            
            expected_requirements = f"""Expected Slide Title: {slide_title}
Expected Chart Instruction: {expected_chart_instruction}
Expected Summary Instruction: {expected_summary_instruction}"""
            
            qa_query = critic_user_prompt_template.format(
                slide_content=slide_content,
                expected_requirements=expected_requirements,
                quality_standards=quality_assurance_params.get('quality_standards', ''),
                review_criteria=quality_assurance_params.get('review_criteria', '')
            )
            
            qa_result = asyncio.run(compiled_critic_agent.invoke(qa_query))
            slide_qa_results[slide_key] = qa_result
            
            if chart_path and Path(chart_path).exists():
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path=chart_path,
                    summary_text=formatted_summary,
                    layout_params=layout_params,
                    styling_params=styling_params
                )
            else:
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path="",
                    summary_text=formatted_summary,
                    layout_params=layout_params,
                    styling_params=styling_params
                )
            
            slide_presentations.append(slide_prs)
        
        final_presentation = combine_presentations(slide_presentations)
        return final_presentation, slide_charts_dict, slide_summaries_dict

    except Exception as e:
        logger.error(f"Multi-agent workflow failed: {str(e)}", exc_info=True)
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_placeholder = slide.shapes.title
        subtitle_placeholder = slide.placeholders[1]
        title_placeholder.text = "Multi-Agent Workflow Error"
        subtitle_placeholder.text = f"Error: {str(e)}\nPlease check the logs for details."
        return prs, {}, {}


def _format_summary_text(summary_text: str) -> str:
    """Format and clean summary text for presentation."""
    if not summary_text:
        return ""
    
    lines = summary_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if 'slide title' in line.lower() or 'slide_title' in line.lower():
            continue
        
        line = line.lstrip('•').lstrip('*').lstrip('-').lstrip(' ').strip()
        
        if len(line) < 3:
            continue
        
        if any(placeholder in line.lower() for placeholder in ['$x', 'please fill', 'placeholder', 'fill in']):
            continue
        
        if not line.startswith('•'):
            formatted_lines.append(f"• {line}")
        else:
            formatted_lines.append(line)
    
    formatted = '\n'.join(formatted_lines)
    
    if not formatted_lines:
        formatted = f"• {summary_text.strip()}"
    
    return formatted


def _format_agent_response(result: dict[str, Any]) -> str:
    """Format agent response for readable logging output."""
    if not result:
        return "No response"
    
    formatted = []
    if result.get('success'):
        formatted.append("✓ Success")
    else:
        formatted.append(f"✗ Failed: {result.get('error', 'Unknown error')}")
    
    if 'plan' in result:
        plan = result['plan']
        if isinstance(plan, dict):
            formatted.append(f"Plan: {str(plan.get('plan_text', plan))[:200]}...")
        else:
            formatted.append(f"Plan: {str(plan)[:200]}...")
    
    if 'chart_data' in result:
        formatted.append(f"Chart Data: {str(result['chart_data'])[:200]}...")
    
    if 'summary' in result:
        summary = result['summary']
        if isinstance(summary, dict):
            formatted.append(f"Summary: {str(summary.get('summary_text', summary))[:200]}...")
        else:
            formatted.append(f"Summary: {str(summary)[:200]}...")
    
    if 'feedback' in result:
        feedback = result['feedback']
        if isinstance(feedback, dict):
            formatted.append(f"Feedback: {str(feedback.get('feedback_text', feedback))[:200]}...")
        else:
            formatted.append(f"Feedback: {str(feedback)[:200]}...")
    
    if 'quality_score' in result:
        formatted.append(f"Quality Score: {result['quality_score']}/10")
    
    return "\n".join(formatted) if formatted else str(result)


def _generate_chart_for_slide_with_logging(
    chart_instruction: str,
    slide_key: str,
    chart_agent: ChartGeneratorAgent,
    agent_query: str
) -> tuple[str, Any]:
    """Generate chart with logging. Returns (chart_path, matplotlib.Figure) for partition dataset."""
    try:
        chart_result = asyncio.run(chart_agent.invoke(agent_query))
        
        chart_path = None
        if chart_result.get('success'):
            chart_data = chart_result.get('chart_data', {})
            if isinstance(chart_data, dict):
                chart_path = chart_data.get('chart_path')
            elif isinstance(chart_data, str):
                try:
                    import json
                    parsed = json.loads(chart_data)
                    chart_path = parsed.get('chart_path')
                except:
                    pass
        
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
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{chart_instruction[:50]}...", 
               ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")
        
        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        return str(chart_path), fig
        
    except Exception as e:
        logger.error(f"Error generating chart for {slide_key}: {str(e)}")
        return "", None


def _generate_summary_for_slide_with_logging(
    summary_instruction: str,
    slide_key: str,
    summarizer_agent: SummarizerAgent,
    agent_query: str
) -> str:
    """Generate summary text with logging."""
    try:
        summary_result = asyncio.run(summarizer_agent.invoke(agent_query))
        
        if summary_result.get('success'):
            summary_content = summary_result.get('summary', {})
            summary_text = ''
            
            if isinstance(summary_content, dict):
                summary_text = summary_content.get('summary_text', '')
                if not summary_text:
                    summary_text = summary_content.get('text', '') or summary_content.get('content', '')
                if not summary_text:
                    summary_str = str(summary_content)
                    try:
                        import json
                        if summary_str.startswith('{'):
                            parsed = json.loads(summary_str)
                            summary_text = parsed.get('summary_text', '')
                    except:
                        pass
                    if not summary_text:
                        summary_text = summary_str
            elif isinstance(summary_content, str):
                try:
                    import json
                    if summary_content.strip().startswith('{'):
                        parsed = json.loads(summary_content)
                        summary_text = parsed.get('summary_text', '') or parsed.get('text', '')
                except:
                    pass
                if not summary_text:
                    summary_text = summary_content
            else:
                summary_text = str(summary_content)
            
            if summary_text:
                summary_text = summary_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                summary_text = '\n'.join(line.strip() for line in summary_text.split('\n') if line.strip())
                return summary_text
        
        return f"• Analysis for {slide_key}\n• Data insights generated based on: {summary_instruction[:100]}..."
        
    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return f"• Analysis for {slide_key}\n• Data insights generated"
