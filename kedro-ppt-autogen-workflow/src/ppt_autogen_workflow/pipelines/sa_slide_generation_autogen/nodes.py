"""Kedro nodes for single-agent AutoGen PPT generation pipeline."""
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
from .agent import create_ppt_agent, PPTGenerationAgent
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def init_tools(sales_data: pd.DataFrame) -> dict[str, Any]:
    """Initialize all tools needed for PPT generation agent."""
    from .tools import build_tools
    return {"ppt_tools": build_tools(sales_data)}


def compile_ppt_agent(
    slide_generation_requirements: dict[str, Any],
    ppt_generator_system_prompt: Any,
    model_client: OpenAIChatCompletionClient,
    tools: dict[str, Any],
) -> PPTGenerationAgent:
    """Compile the PPT Generation Agent with requirements."""
    try:
        slide_definitions = parse_instructions_yaml(slide_generation_requirements)
        
        ppt_requirement = {
            'slides': {},
        }
        
        data_context = "Sales data available through agent tools"
        
        for slide_key, slide_config in slide_definitions.items():
            objective = slide_config.get('objective', {})
            slide_title = objective.get('slide_title', slide_key)
            chart_instruction = objective.get('chart_instruction', '')
            summary_instruction = objective.get('summary_instruction', '')
            
            ppt_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }
        
        system_prompt_text = ppt_generator_system_prompt.format()
        ppt_tools = tools["ppt_tools"]
        agent = create_ppt_agent(model_client, system_prompt_text, ppt_tools)
        agent._ppt_requirement = ppt_requirement
        agent._tools = ppt_tools
        return agent
    except Exception as e:
        logger.error(f"Failed to compile PPT agent: {str(e)}", exc_info=True)
        raise


def generate_presentation(
    compiled_ppt_agent: PPTGenerationAgent,
) -> Any:
    """Generate presentation using compiled agent and stored requirements."""
    try:
        ppt_requirement = compiled_ppt_agent._ppt_requirement
        slide_configs = ppt_requirement['slides']
        slide_presentations = []

        for slide_key, config in slide_configs.items():
            slide_title = config['slide_title']
            chart_instruction = config.get('chart_instruction', '')
            summary_instruction = config.get('summary_instruction', '')

            chart_path, chart_fig = _generate_chart_for_slide(
                compiled_ppt_agent, chart_instruction, slide_key
            )

            summary_text = _generate_summary_for_slide(
                compiled_ppt_agent, summary_instruction, slide_key, chart_path
            )

            formatted_summary = _format_summary_text(summary_text)

            if chart_path and Path(chart_path).exists():
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path=chart_path,
                    summary_text=formatted_summary
                )
            else:
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path="",
                    summary_text=formatted_summary
                )

            slide_presentations.append(slide_prs)

        final_presentation = combine_presentations(slide_presentations)
        return final_presentation

    except Exception as e:
        logger.error(f"PPT generation failed: {str(e)}", exc_info=True)
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_placeholder = slide.shapes.title
        subtitle_placeholder = slide.placeholders[1]
        title_placeholder.text = "Error in Presentation Generation"
        subtitle_placeholder.text = f"Error: {str(e)}"
        return prs


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
    
    if 'content' in result:
        content = result['content']
        if isinstance(content, dict):
            formatted.append(f"Content: {str(content)[:200]}...")
        else:
            formatted.append(f"Content: {str(content)[:200]}...")
    
    return "\n".join(formatted) if formatted else str(result)


def _generate_chart_for_slide(
    agent: PPTGenerationAgent,
    chart_instruction: str,
    slide_key: str
) -> tuple[str, Any]:
    """Generate chart for a slide by invoking agent with tools. Returns (chart_path, matplotlib.Figure)."""
    try:
        query = f"""Please generate a chart for this slide using the generate_sales_chart tool.

Chart Instruction: {chart_instruction}

Please use the generate_sales_chart tool with the chart instruction above to create the chart. Return the chart path."""
        
        chart_result = asyncio.run(agent.invoke(query))
        
        chart_path = None
        if chart_result.get('success'):
            content = chart_result.get('content', {})
            if isinstance(content, dict):
                chart_path = content.get('chart_path')
                if not chart_path:
                    tools_used = chart_result.get('tools_used', [])
                    if tools_used:
                        chart_path = content.get('chart_path') or content.get('path')
            elif isinstance(content, str):
                try:
                    import json
                    if content.strip().startswith('{'):
                        parsed = json.loads(content)
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


def _generate_summary_for_slide(
    agent: PPTGenerationAgent,
    summary_instruction: str,
    slide_key: str,
    chart_path: str = None
) -> str:
    """Generate summary text for a slide by invoking agent with tools."""
    try:
        chart_status = f"Chart has been generated: {chart_path if chart_path and Path(chart_path).exists() else 'Chart generation in progress'}"
        
        query = f"""Please generate a summary for this slide using the generate_business_summary tool.

Summary Instruction: {summary_instruction}
Chart Status: {chart_status}

IMPORTANT:
1. Use the generate_business_summary tool with the summary instruction above to get actual calculated values
2. DO NOT include the slide title in your summary output
3. DO NOT use placeholders like "$X million" - use actual calculated values from the tool
4. Return the summary text with real numbers and insights"""
        
        summary_result = asyncio.run(agent.invoke(query))
        
        if summary_result.get('success'):
            content = summary_result.get('content', {})
            summary_text = ''
            
            if isinstance(content, dict):
                summary_text = content.get('summary_text', '')
                if not summary_text:
                    summary_text = content.get('text', '') or content.get('content', '')
                if not summary_text:
                    summary_str = str(content)
                    try:
                        import json
                        if summary_str.startswith('{'):
                            parsed = json.loads(summary_str)
                            summary_text = parsed.get('summary_text', '')
                    except:
                        pass
                    if not summary_text:
                        summary_text = summary_str
            elif isinstance(content, str):
                try:
                    import json
                    if content.strip().startswith('{'):
                        parsed = json.loads(content)
                        summary_text = parsed.get('summary_text', '') or parsed.get('text', '')
                except:
                    pass
                if not summary_text:
                    summary_text = content
            else:
                summary_text = str(content)
            
            if summary_text:
                summary_text = summary_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                summary_text = '\n'.join(line.strip() for line in summary_text.split('\n') if line.strip())
                return summary_text
        
        return f"• Analysis for {slide_key}\n• Data insights generated based on: {summary_instruction[:100]}..."
        
    except Exception as e:
        logger.error(f"Error generating summary for {slide_key}: {str(e)}")
        return f"• Analysis for {slide_key}\n• Data insights generated"
