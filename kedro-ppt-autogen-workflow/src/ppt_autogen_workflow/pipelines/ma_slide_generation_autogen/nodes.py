"""Kedro nodes for multi-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Any
from pathlib import Path

# Set matplotlib to use non-interactive backend before importing pyplot
# This prevents GUI window creation issues on macOS when running in threads
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

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

# Import utility functions
from ppt_autogen_workflow.utils.chart_generator import generate_chart
from ppt_autogen_workflow.utils.summary_generator import generate_summary
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def init_tools(sales_data: pd.DataFrame) -> dict[str, Any]:
    """Initialize all tools needed for PPT generation agents.

    Args:
        sales_data: Sales data DataFrame for tool initialization

    Returns:
        Dictionary containing all tools organized by agent type
    """
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
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Analyze requirements and create structured requirement objects for each agent type.

    This node parses slide_generation_requirements and creates agent-specific requirement
    objects. Each agent will use its requirement object to format user prompts during compilation.

    Args:
        slide_generation_requirements: YAML dict with slide definitions
        styling_params: Styling parameters from params:styling
        layout_params: Layout parameters from params:layout

    Returns:
        Tuple of (planner_requirements, chart_requirements, summarizer_requirements)
        Each requirement is a dict with 'slides' key containing slide-specific requirements
    """
    logger.info("=" * 80)
    logger.info("ANALYZING REQUIREMENTS - Creating agent-specific requirements")
    logger.info("=" * 80)

    try:
        # Parse slide requirements
        slide_definitions = parse_instructions_yaml(slide_generation_requirements)
        logger.info(f"✓ Found {len(slide_definitions)} slide definitions")

        # Initialize requirement structures
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

            # Planner requirement: Full context for planning
            planner_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }

            # Chart requirement: Chart-specific information
            chart_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'chart_instruction': chart_instruction,
                'data_context': data_context,
            }

            # Summarizer requirement: Summary-specific information
            summarizer_requirement['slides'][slide_key] = {
                'slide_title': slide_title,
                'summary_instruction': summary_instruction,
                'data_context': data_context,
            }

            logger.info(f"  ✓ Analyzed requirements for slide: {slide_key}")

        logger.info(f"✓ Created requirements for {len(slide_definitions)} slides")
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
    """Compile the Planner Agent.

    Args:
        planner_system_prompt: System prompt for the planner
        planner_requirement: Planner requirement object from analyze_requirements
        model_client: LLM client
        tools: Tools dictionary (sales_data is embedded in tools)

    Returns:
        Compiled planner agent
    """
    logger.info("=" * 80)
    logger.info("COMPILING PLANNER AGENT")
    logger.info("=" * 80)

    try:
        # Extract planner tools
        planner_tools = tools["planner_tools"]

        # Format system prompt
        system_prompt_text = planner_system_prompt.format()

        # Create the planner agent
        agent = create_planner_agent(model_client, system_prompt_text, planner_tools)
        
        # Store requirement in agent for later use
        agent._planner_requirement = planner_requirement

        logger.info(f"✓ Planner agent compiled")
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
    """Compile Chart Generator Agent and format user prompts using chart requirements.

    Formats user prompts for each slide using chart_requirement and stores them in agent context.

    Args:
        chart_requirement: Chart requirement object from analyze_requirements
        chart_generator_system_prompt: System prompt for chart generator
        chart_generator_user_prompt: User prompt template
        model_client: LLM client
        tools: Tools dictionary

    Returns:
        Compiled chart generator agent with formatted prompts stored in context
    """
    logger.info("Compiling Chart Generator Agent with chart requirements")

    try:
        system_prompt_text = chart_generator_system_prompt.format()
        chart_generator_tools = tools["chart_generator_tools"]

        agent = create_chart_generator_agent(model_client, system_prompt_text, chart_generator_tools)
        
        # Format user prompts for each slide using chart requirements
        formatted_prompts = {}
        for slide_key, slide_config in chart_requirement['slides'].items():
            slide_title = slide_config['slide_title']
            chart_instruction = slide_config['chart_instruction']
            data_context = slide_config['data_context']
            
            # Format planner_analysis for this slide (inject via placeholder)
            planner_analysis = f"Slide Title: {slide_title}\nChart Instruction: {chart_instruction}\nData Context: {data_context}"
            
            # Format user prompt using template
            formatted_prompt = chart_generator_user_prompt.format(
                planner_analysis=planner_analysis
            )
            formatted_prompts[slide_key] = formatted_prompt
        
        # Store formatted prompts and requirement in agent
        agent._formatted_prompts = formatted_prompts
        agent._chart_requirement = chart_requirement
        
        logger.info(f"✓ Chart Generator agent compiled with {len(formatted_prompts)} formatted prompts")
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
    """Compile Summarizer Agent and format user prompts using summarizer requirements.

    Formats user prompts for each slide using summarizer_requirement and stores them in agent context.
    Chart status will be injected during orchestration.

    Args:
        summarizer_requirement: Summarizer requirement object from analyze_requirements
        summarizer_system_prompt: System prompt for summarizer
        summarizer_user_prompt: User prompt template
        model_client: LLM client
        tools: Tools dictionary

    Returns:
        Compiled summarizer agent with formatted prompts stored in context
    """
    logger.info("Compiling Summarizer Agent with summarizer requirements")

    try:
        system_prompt_text = summarizer_system_prompt.format()
        summarizer_tools = tools["summarizer_tools"]

        agent = create_summarizer_agent(model_client, system_prompt_text, summarizer_tools)
        
        # Format user prompts for each slide using summarizer requirements
        # Note: chart_status will be injected during orchestration
        formatted_prompts = {}
        for slide_key, slide_config in summarizer_requirement['slides'].items():
            slide_title = slide_config['slide_title']
            summary_instruction = slide_config['summary_instruction']
            data_context = slide_config['data_context']
            
            # Format planner_analysis for this slide (inject via placeholder)
            # Note: Slide title is NOT included - it's only for slide creation, not summary content
            planner_analysis = f"Summary Instruction: {summary_instruction}\nData Context: {data_context}"
            
            # Format user prompt using template (chart_status will be added during orchestration)
            formatted_prompt = summarizer_user_prompt.format(
                planner_analysis=planner_analysis,
                chart_status="{chart_status}"  # Placeholder to be replaced during orchestration
            )
            formatted_prompts[slide_key] = formatted_prompt
        
        # Store formatted prompts and requirement in agent
        agent._formatted_prompts = formatted_prompts
        agent._summarizer_requirement = summarizer_requirement
        agent._user_prompt_template = summarizer_user_prompt  # Keep template for chart_status injection
        
        logger.info(f"✓ Summarizer agent compiled with {len(formatted_prompts)} formatted prompts")
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
    """Compile Critic Agent and prepare for prompt formatting.

    Stores user prompt template and quality assurance parameters. Prompts will be formatted
    during orchestration when slide content and expected requirements are available.

    Args:
        critic_system_prompt: System prompt for critic
        critic_user_prompt: User prompt template
        quality_assurance_params: Quality assurance parameters
        model_client: LLM client
        tools: Tools dictionary

    Returns:
        Compiled critic agent with template and quality params stored in context
    """
    logger.info("Compiling Critic Agent")

    try:
        system_prompt_text = critic_system_prompt.format()
        critic_tools = tools["critic_tools"]

        agent = create_critic_agent(model_client, system_prompt_text, critic_tools)
        
        # Store template and quality params for later formatting
        agent._user_prompt_template = critic_user_prompt
        agent._quality_assurance_params = quality_assurance_params
        
        logger.info("✓ Critic agent compiled successfully")
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
    """
    Orchestrate multi-agent workflow in round-robin fashion - LIGHTWEIGHT COORDINATOR.

    This function is extremely lightweight - it ONLY coordinates agents in round-robin execution.

    The orchestrator's only job:
    1. Extract formatted prompts from agents (already formatted during compilation)
    2. Loop through slides from planner_requirement
    3. Inject dynamic values (chart_status, slide_content) into pre-formatted prompts
    4. Call agents in sequence: Chart Generator → Summarizer → Critic
    5. Collect and combine results

    Args:
        compiled_planner_agent: Planner agent (contains planner_requirement in context)
        compiled_chart_agent: Chart generator agent (with formatted prompts in context)
        compiled_summarizer_agent: Summarizer agent (with formatted prompts in context)
        compiled_critic_agent: Critic agent (with requirement, template, and quality_assurance_params in context)

    Returns:
        (final_presentation, slide_charts_dict, slide_summaries_dict)
        Charts and summaries are saved as partition datasets (PNG/TXT files)
    """
    logger.info("=" * 80)
    logger.info("LIGHTWEIGHT ORCHESTRATION: Round-robin agent execution")
    logger.info("=" * 80)

    try:
        # Extract requirements from agents (formatted during compilation)
        planner_requirement = compiled_planner_agent._planner_requirement
        chart_formatted_prompts = compiled_chart_agent._formatted_prompts
        chart_requirement = compiled_chart_agent._chart_requirement
        summarizer_formatted_prompts = compiled_summarizer_agent._formatted_prompts
        summarizer_user_prompt_template = compiled_summarizer_agent._user_prompt_template
        critic_user_prompt_template = compiled_critic_agent._user_prompt_template
        quality_assurance_params = compiled_critic_agent._quality_assurance_params
        
        # Extract layout and styling parameters for slide creation
        layout_params = planner_requirement.get('layout', {})
        styling_params = planner_requirement.get('styling', {})
        
        slide_configs = planner_requirement['slides']
        logger.info(f"✓ Coordinating {len(slide_configs)} slides in round-robin pattern")

        # Store intermediate results for partition datasets
        # Keys are partition names (slide_key), values are data to save
        slide_charts_dict = {}  # Dict[partition_key, matplotlib.Figure]
        slide_summaries_dict = {}  # Dict[partition_key, str]
        slide_presentations = []
        slide_qa_results = {}

        # Process each slide with multi-agent collaboration
        for slide_key, config in slide_configs.items():
            logger.info("=" * 80)
            logger.info(f"Processing {slide_key}: {config['slide_title']}")
            logger.info("=" * 80)
            
            # Extract chart_instruction for helper function (still needed for logging/fallback)
            chart_instruction = config.get('chart_instruction', '')
            
            # ===================================================================
            # MULTI-AGENT CONVERSATION: Round-robin collaboration
            # ===================================================================
            logger.info(f"\n[CONVERSATION LOOP] Starting multi-agent collaboration for {slide_key}")
            logger.info("-" * 80)

            # Step 1: Chart agent generates chart (using pre-formatted prompt)
            logger.info(f"[AGENT: ChartGenerator] Generating chart for {slide_key}...")
            chart_query = chart_formatted_prompts.get(slide_key, '')
            
            logger.info(f"[LLM CALL] Chart Generator Agent Query:\n{chart_query}")
            chart_path, chart_fig = _generate_chart_for_slide_with_logging(
                chart_instruction, slide_key, compiled_chart_agent, chart_query
            )
            
            # Save chart figure for partition dataset
            if chart_fig is not None:
                slide_charts_dict[slide_key] = chart_fig
                logger.info(f"✓ Chart figure saved to partition dataset with key: {slide_key}")
            
            # Step 2: Summarizer agent generates summary (inject chart_status into pre-formatted prompt)
            logger.info(f"\n[AGENT: Summarizer] Generating summary for {slide_key}...")
            
            # Inject chart_status into pre-formatted prompt
            chart_status = f"Chart has been generated: {chart_path if chart_path else 'Chart generation in progress'}"
            summary_query = summarizer_formatted_prompts.get(slide_key, '').replace('{chart_status}', chart_status)
            
            logger.info(f"[LLM CALL] Summarizer Agent Query:\n{summary_query}")
            # Extract summary_instruction for helper function (still needed for logging/fallback)
            summary_instruction = config.get('summary_instruction', '')
            summary_text = _generate_summary_for_slide_with_logging(
                summary_instruction, slide_key, compiled_summarizer_agent, summary_query
            )
            
            # Format and clean summary text
            formatted_summary = _format_summary_text(summary_text)
            
            # Save summary text for partition dataset
            slide_summaries_dict[slide_key] = formatted_summary
            logger.info(f"✓ Summary text saved to partition dataset with key: {slide_key}")
            
            # Step 3: Critic agent QA review (format prompt with slide content and expected requirements)
            logger.info(f"\n[AGENT: Critic] Quality assurance review for {slide_key}...")
            
            # Extract expected requirements from config for validation
            slide_title = config['slide_title']
            expected_chart_instruction = config.get('chart_instruction', '')
            expected_summary_instruction = config.get('summary_instruction', '')
            
            # Format user prompt with slide content, expected requirements, and quality parameters
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
            
            logger.info(f"[LLM CALL] Critic Agent Query:\n{qa_query}")
            qa_result = asyncio.run(compiled_critic_agent.invoke(qa_query))
            logger.info(f"[LLM RESPONSE] Critic Agent QA Response:\n{_format_agent_response(qa_result)}")
            
            slide_qa_results[slide_key] = qa_result
            quality_score = qa_result.get('quality_score', 0.0)
            logger.info(f"✓ QA Complete - Quality Score: {quality_score}/10")
            
            # Log conversation summary
            logger.info("-" * 80)
            logger.info(f"[CONVERSATION SUMMARY] {slide_key}:")
            logger.info(f"  - ChartGenerator: Generated chart")
            logger.info(f"  - Summarizer: Generated summary")
            logger.info(f"  - Critic: QA Score {quality_score}/10")
            logger.info("-" * 80)
            
            # Create slide presentation with layout and styling parameters
            logger.info(f"\nCreating slide presentation for {slide_key}...")
            if chart_path and Path(chart_path).exists():
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path=chart_path,
                    summary_text=formatted_summary,
                    layout_params=layout_params,
                    styling_params=styling_params
                )
            else:
                # Create slide without chart if chart generation failed
                logger.warning(f"  Chart path not available for {slide_key}, creating slide without chart")
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path="",  # Empty path - will be handled by create_slide
                    summary_text=formatted_summary,
                    layout_params=layout_params,
                    styling_params=styling_params
                )
            
            slide_presentations.append(slide_prs)
            logger.info(f"✓ Slide {slide_key} created successfully\n")
        
        # Combine all slides into final presentation
        logger.info("=" * 80)
        logger.info("Step 2: Combining all slides into final presentation...")
        final_presentation = combine_presentations(slide_presentations)
        
        # Log final QA summary
        logger.info("=" * 80)
        logger.info("FINAL QA SUMMARY:")
        for slide_key, qa_result in slide_qa_results.items():
            score = qa_result.get('quality_score', 0.0)
            logger.info(f"  {slide_key}: {score}/10")
        avg_score = sum(r.get('quality_score', 0.0) for r in slide_qa_results.values()) / len(slide_qa_results) if slide_qa_results else 0.0
        logger.info(f"  Average Quality Score: {avg_score:.1f}/10")
        logger.info("=" * 80)
        
        logger.info(f"✓ Multi-agent workflow completed successfully - Created {len(slide_presentations)} slides")
        return final_presentation, slide_charts_dict, slide_summaries_dict

    except Exception as e:
        logger.error(f"Multi-agent workflow failed: {str(e)}", exc_info=True)
        # Return error presentation
        prs = Presentation()
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_placeholder = slide.shapes.title
        subtitle_placeholder = slide.placeholders[1]

        title_placeholder.text = "Multi-Agent Workflow Error"
        subtitle_placeholder.text = f"Error: {str(e)}\nPlease check the logs for details."

        return prs, {}, {}


def _format_summary_text(summary_text: str) -> str:
    """Format and clean summary text for presentation.
    
    Args:
        summary_text: Raw summary text from agent or utility function
        
    Returns:
        Formatted summary text with proper bullet points and line breaks
    """
    if not summary_text:
        return ""
    
    # Split by newlines and clean up
    lines = summary_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove lines that contain "Slide Title:" - this should not be in the summary
        if 'slide title' in line.lower() or 'slide_title' in line.lower():
            continue
        
        # Remove existing bullet points and add proper formatting
        line = line.lstrip('•').lstrip('*').lstrip('-').lstrip(' ').strip()
        
        # Skip lines that are too short or just punctuation
        if len(line) < 3:
            continue
        
        # Skip placeholder text like "$X million" or "Please fill in"
        if any(placeholder in line.lower() for placeholder in ['$x', 'please fill', 'placeholder', 'fill in']):
            continue
        
        # Ensure bullet point format
        if not line.startswith('•'):
            formatted_lines.append(f"• {line}")
        else:
            formatted_lines.append(line)
    
    # Join with newlines
    formatted = '\n'.join(formatted_lines)
    
    # If no bullets were found, add default formatting
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
    
    # Extract key information
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


def _extract_plan_text(plan_result: dict[str, Any]) -> str:
    """Extract plan text from planner agent result."""
    if not plan_result:
        return "No plan available"
    
    plan = plan_result.get('plan', {})
    if isinstance(plan, dict):
        return str(plan.get('plan_text', plan))[:500]
    return str(plan)[:500]


def _generate_chart_for_slide_with_logging(
    chart_instruction: str,
    slide_key: str,
    chart_agent: ChartGeneratorAgent,
    agent_query: str
) -> tuple[str, Any]:
    """Generate chart with logging. Returns (chart_path, matplotlib.Figure) for partition dataset.
    
    Note: Sales data is accessed through agent tools, not passed directly.
    The agent uses tools to generate and save the chart, then we load it as a figure.
    """
    try:
        # Use agent to generate chart (agent has access to data through tools)
        logger.info(f"  Invoking chart agent for {slide_key}...")
        chart_result = asyncio.run(chart_agent.invoke(agent_query))
        logger.info(f"[LLM RESPONSE] Chart Generator Agent Response:\n{_format_agent_response(chart_result)}")
        
        # Try to extract chart path from agent result
        chart_path = None
        if chart_result.get('success'):
            chart_data = chart_result.get('chart_data', {})
            if isinstance(chart_data, dict):
                chart_path = chart_data.get('chart_path')
            elif isinstance(chart_data, str):
                # Try to parse JSON string
                try:
                    import json
                    parsed = json.loads(chart_data)
                    chart_path = parsed.get('chart_path')
                except:
                    pass
        
        # If we have a valid path, load the image and create a figure for partition dataset
        if chart_path and Path(chart_path).exists():
            try:
                from matplotlib.image import imread
                img = imread(chart_path)
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.imshow(img)
                ax.axis('off')
                logger.info(f"  ✓ Chart loaded from: {chart_path}")
                return str(chart_path), fig
            except Exception as e:
                logger.warning(f"  Could not load chart image: {e}")
        
        # Fallback: create a placeholder figure
        logger.warning(f"  Chart path not available from agent, creating placeholder chart...")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, f"Chart for {slide_key}\n{chart_instruction[:50]}...", 
               ha='center', va='center', fontsize=12, wrap=True)
        ax.set_title(f"Chart: {slide_key}")
        
        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        logger.info(f"  ✓ Placeholder chart saved to: {chart_path}")
        return str(chart_path), fig
        
    except Exception as e:
        logger.error(f"  ✗ Error generating chart for {slide_key}: {str(e)}")
        # Return empty path and None figure
        return "", None


def _generate_summary_for_slide_with_logging(
    summary_instruction: str,
    slide_key: str,
    summarizer_agent: SummarizerAgent,
    agent_query: str
) -> str:
    """Generate summary text with logging.
    
    Note: Sales data is accessed through agent tools, not passed directly.
    """
    try:
        # Use agent to generate summary (agent has access to data through tools)
        logger.info(f"  Invoking summarizer agent for {slide_key}...")
        summary_result = asyncio.run(summarizer_agent.invoke(agent_query))
        logger.info(f"[LLM RESPONSE] Summarizer Agent Response:\n{_format_agent_response(summary_result)}")
        
        # Extract summary text from agent result
        if summary_result.get('success'):
            summary_content = summary_result.get('summary', {})
            summary_text = ''
            
            # Try different extraction methods
            if isinstance(summary_content, dict):
                # Check for summary_text first (from tool response)
                summary_text = summary_content.get('summary_text', '')
                # If not found, try other keys
                if not summary_text:
                    summary_text = summary_content.get('text', '') or summary_content.get('content', '')
                # If still not found, try to extract from string representation
                if not summary_text:
                    summary_str = str(summary_content)
                    # Try to parse JSON if it's a JSON string
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
                # Try to parse JSON string if it looks like JSON
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
            
            # Clean up the summary text
            if summary_text:
                # Remove markdown formatting if present
                summary_text = summary_text.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
                # Remove extra whitespace
                summary_text = '\n'.join(line.strip() for line in summary_text.split('\n') if line.strip())
                
                logger.info(f"[SUMMARY GENERATION] Summary length: {len(summary_text)} characters")
                logger.info(f"[SUMMARY GENERATION] Summary preview: {summary_text[:200]}...")
                logger.info(f"  ✓ Summary generated for {slide_key} ({len(summary_text)} chars)")
                return summary_text
        
        # Fallback: use utility function if agent didn't provide summary
        logger.warning(f"  Agent didn't provide summary, using fallback...")
        # Note: This would require accessing data through tools
        # For now, return a default summary
        return f"• Analysis for {slide_key}\n• Data insights generated based on: {summary_instruction[:100]}..."
        
    except Exception as e:
        logger.error(f"  ✗ Error generating summary for {slide_key}: {str(e)}")
        # Return default summary
        return f"• Analysis for {slide_key}\n• Data insights generated"

