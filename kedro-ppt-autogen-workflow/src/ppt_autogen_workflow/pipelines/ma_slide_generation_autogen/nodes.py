"""Kedro nodes for multi-agent AutoGen PPT generation pipeline."""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Any
from pathlib import Path

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

# Import utility functions
from ppt_autogen_workflow.utils.chart_generator import generate_chart
from ppt_autogen_workflow.utils.summary_generator import generate_summary
from ppt_autogen_workflow.utils.ppt_builder import create_slide, combine_presentations
from ppt_autogen_workflow.utils.instruction_parser import parse_instructions_yaml

logger = logging.getLogger(__name__)


def initialize_planner_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame,
) -> PlannerAgent:
    """Initialize and compile the PlannerAgent with sales data access.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled PlannerAgent ready for invocation
    """
    logger.info("Initializing planner agent...")

    try:
        agent = create_planner_agent(model_client, sales_data)
        logger.info("✓ Planner agent initialized and compiled successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize planner agent: {str(e)}")
        raise


def initialize_chart_generator_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame,
) -> ChartGeneratorAgent:
    """Initialize and compile the ChartGeneratorAgent with sales data access.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled ChartGeneratorAgent ready for invocation
    """
    logger.info("Initializing chart generator agent...")

    try:
        agent = create_chart_generator_agent(model_client, sales_data)
        logger.info("✓ Chart generator agent initialized and compiled successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize chart generator agent: {str(e)}")
        raise


def initialize_summarizer_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame,
) -> SummarizerAgent:
    """Initialize and compile the SummarizerAgent with sales data access.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame for tool access

    Returns:
        Compiled SummarizerAgent ready for invocation
    """
    logger.info("Initializing summarizer agent...")

    try:
        agent = create_summarizer_agent(model_client, sales_data)
        logger.info("✓ Summarizer agent initialized and compiled successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize summarizer agent: {str(e)}")
        raise


def initialize_critic_agent(
    model_client: OpenAIChatCompletionClient,
    sales_data: pd.DataFrame,
) -> CriticAgent:
    """Initialize and compile the CriticAgent.

    Args:
        model_client: Pre-configured OpenAI chat completion client
        sales_data: Sales data DataFrame (passed for consistency, not used by critic tools)

    Returns:
        Compiled CriticAgent ready for invocation
    """
    logger.info("Initializing critic agent...")

    try:
        agent = create_critic_agent(model_client, sales_data)
        logger.info("✓ Critic agent initialized and compiled successfully")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize critic agent: {str(e)}")
        raise


def orchestrate_multi_agent_workflow(
    planner_agent: PlannerAgent,
    chart_agent: ChartGeneratorAgent,
    summarizer_agent: SummarizerAgent,
    critic_agent: CriticAgent,
    instructions_yaml: dict[str, Any],
    sales_data: Any,
    user_query: str
) -> tuple[Any, dict[str, plt.Figure], dict[str, str]]:
    """
    Orchestrate multi-agent workflow: parse instructions_yaml, generate slides with agent collaboration.
    
    Returns:
        (final_presentation, slide_charts_dict, slide_summaries_dict)
        Charts and summaries are saved as partition datasets (PNG/TXT files)
    """
    logger.info("=" * 80)
    logger.info("Starting multi-agent workflow orchestration with instructions and sales data...")
    logger.info("=" * 80)
    
    try:
        # Parse instructions_yaml structure
        logger.info("Step 1: Parsing instructions_yaml structure...")
        slide_definitions = parse_instructions_yaml(instructions_yaml)
        logger.info(f"✓ Found {len(slide_definitions)} slide definitions in instructions_yaml")
        
        # Ensure sales_data is a DataFrame
        if not isinstance(sales_data, pd.DataFrame):
            sales_data = pd.DataFrame(sales_data) if sales_data is not None else pd.DataFrame()
        
        # Store intermediate results for partition datasets
        # Keys are partition names (slide_key), values are data to save
        slide_charts_dict = {}  # Dict[partition_key, matplotlib.Figure]
        slide_summaries_dict = {}  # Dict[partition_key, str]
        slide_presentations = []
        slide_qa_results = {}
        
        # Process each slide definition with multi-agent collaboration
        for slide_key, slide_config in slide_definitions.items():
            logger.info("=" * 80)
            logger.info(f"Processing {slide_key}: {slide_config.get('objective', {}).get('slide_title', 'Untitled')}")
            logger.info("=" * 80)
            
            objective = slide_config.get('objective', {})
            chart_instruction = objective.get('chart_instruction', '')
            summary_instruction = objective.get('summary_instruction', '')
            slide_title = objective.get('slide_title', slide_key)
            
            # ===================================================================
            # MULTI-AGENT CONVERSATION: Round-robin collaboration
            # ===================================================================
            logger.info(f"\n[CONVERSATION LOOP] Starting multi-agent collaboration for {slide_key}")
            logger.info("-" * 80)
            
            # Step 1: Planner agent analyzes requirements
            logger.info(f"[AGENT: Planner] Analyzing requirements for {slide_key}...")
            planner_query = f"""
            Slide: {slide_key}
            Title: {slide_title}
            Chart Instruction: {chart_instruction}
            Summary Instruction: {summary_instruction}
            
            Please analyze these requirements and provide a plan for generating the chart and summary.
            Consider the sales data context: {len(sales_data)} records available.
            """
            
            logger.info(f"[LLM CALL] Planner Agent Query:\n{planner_query}")
            plan_result = asyncio.run(planner_agent.invoke(planner_query))
            logger.info(f"[LLM RESPONSE] Planner Agent Response:\n{_format_agent_response(plan_result)}")
            
            # Step 2: Chart agent generates chart (with planner context)
            logger.info(f"\n[AGENT: ChartGenerator] Generating chart for {slide_key}...")
            chart_query = f"""
            Based on the planner's analysis: {_extract_plan_text(plan_result)}
            
            Chart Instruction: {chart_instruction}
            Slide Title: {slide_title}
            
            Generate a chart visualization following the instruction exactly.
            """
            
            logger.info(f"[LLM CALL] Chart Generator Agent Query:\n{chart_query}")
            chart_path, chart_fig = _generate_chart_for_slide_with_logging(
                sales_data, chart_instruction, slide_key, chart_agent, chart_query
            )
            
            # Save chart figure for partition dataset
            if chart_fig is not None:
                slide_charts_dict[slide_key] = chart_fig
                logger.info(f"✓ Chart figure saved to partition dataset with key: {slide_key}")
            
            # Step 3: Summarizer agent generates summary (with chart context)
            logger.info(f"\n[AGENT: Summarizer] Generating summary for {slide_key}...")
            summary_query = f"""
            Based on the planner's analysis: {_extract_plan_text(plan_result)}
            Chart has been generated: {chart_path if chart_path else 'Chart generation in progress'}
            
            Summary Instruction: {summary_instruction}
            Slide Title: {slide_title}
            
            Generate a summary following the instruction exactly.
            """
            
            logger.info(f"[LLM CALL] Summarizer Agent Query:\n{summary_query}")
            summary_text = _generate_summary_for_slide_with_logging(
                sales_data, summary_instruction, slide_key, summarizer_agent, summary_query
            )
            
            # Save summary text for partition dataset
            slide_summaries_dict[slide_key] = summary_text
            logger.info(f"✓ Summary text saved to partition dataset with key: {slide_key}")
            
            # Step 4: Critic agent QA review
            logger.info(f"\n[AGENT: Critic] Quality assurance review for {slide_key}...")
            qa_query = f"""
            Review the following slide for quality:
            
            Slide Title: {slide_title}
            Chart Instruction: {chart_instruction}
            Summary Instruction: {summary_instruction}
            
            Generated Chart: {'Available' if chart_path and Path(chart_path).exists() else 'Not available'}
            Generated Summary: {summary_text[:200]}...
            
            Please provide:
            1. Quality score (1-10)
            2. Feedback on chart alignment with instruction
            3. Feedback on summary alignment with instruction
            4. Recommendations for improvement
            5. Overall assessment
            """
            
            logger.info(f"[LLM CALL] Critic Agent Query:\n{qa_query}")
            qa_result = asyncio.run(critic_agent.invoke(qa_query))
            logger.info(f"[LLM RESPONSE] Critic Agent QA Response:\n{_format_agent_response(qa_result)}")
            
            slide_qa_results[slide_key] = qa_result
            quality_score = qa_result.get('quality_score', 0.0)
            logger.info(f"✓ QA Complete - Quality Score: {quality_score}/10")
            
            # Log conversation summary
            logger.info("-" * 80)
            logger.info(f"[CONVERSATION SUMMARY] {slide_key}:")
            logger.info(f"  - Planner: Analyzed requirements")
            logger.info(f"  - ChartGenerator: Generated chart")
            logger.info(f"  - Summarizer: Generated summary")
            logger.info(f"  - Critic: QA Score {quality_score}/10")
            logger.info("-" * 80)
            
            # Create slide presentation
            logger.info(f"\nCreating slide presentation for {slide_key}...")
            if chart_path and Path(chart_path).exists():
                slide_prs = create_slide(
                    slide_title=slide_title,
                    chart_path=chart_path,
                    summary_text=summary_text
                )
            else:
                # Create slide without chart if chart generation failed
                logger.warning(f"  Chart path not available for {slide_key}, creating slide without chart")
                slide_prs = Presentation()
                slide_layout = slide_prs.slide_layouts[1]  # Title and Content layout
                slide = slide_prs.slides.add_slide(slide_layout)
                slide.shapes.title.text = slide_title
                slide.placeholders[1].text = summary_text if summary_text else f"Content for {slide_title}"
            
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
        subtitle_placeholder.text = f"Error: {str(e)}\nQuery: {user_query}"
        
        return prs, {}, {}


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
    sales_data: pd.DataFrame,
    chart_instruction: str,
    slide_key: str,
    chart_agent: ChartGeneratorAgent,
    agent_query: str
) -> tuple[str, Any]:
    """Generate chart with logging. Returns (chart_path, matplotlib.Figure) for partition dataset."""
    try:
        # Use direct utility function for chart generation (more reliable for structured workflow)
        fig = generate_chart(sales_data, chart_instruction)
        
        # Save chart to temporary file
        temp_dir = Path(tempfile.mkdtemp())
        chart_path = temp_dir / f"chart_{slide_key}.png"
        fig.savefig(chart_path, dpi=300, bbox_inches='tight')
        
        logger.info(f"[CHART GENERATION] Chart saved to: {chart_path}")
        logger.info(f"[CHART GENERATION] Chart type: {type(fig)}")
        
        # Don't close figure - we need it for partition dataset
        # plt.close(fig)  # Commented out - need figure for partition dataset
        
        logger.info(f"  ✓ Chart generated and saved: {chart_path}")
        return str(chart_path), fig
        
    except Exception as e:
        logger.error(f"  ✗ Error generating chart for {slide_key}: {str(e)}")
        # Try fallback: use agent if utility function fails
        try:
            logger.info(f"  Attempting fallback to chart agent for {slide_key}...")
            chart_result = asyncio.run(chart_agent.invoke(agent_query))
            logger.info(f"[LLM RESPONSE] Chart Generator Agent Response:\n{_format_agent_response(chart_result)}")
            # Extract chart path from agent result if available
            if chart_result.get('success') and 'chart_path' in str(chart_result):
                chart_path = str(chart_result.get('chart_path', ''))
                # If path exists, we still need a figure - regenerate or return None
                if Path(chart_path).exists():
                    # Re-read the chart instruction and generate figure
                    try:
                        fig = generate_chart(sales_data, chart_instruction)
                        return chart_path, fig
                    except:
                        return chart_path, None
        except Exception as fallback_error:
            logger.error(f"  Fallback to agent also failed: {str(fallback_error)}")
        
        # Return empty path and None figure
        return "", None


def _generate_summary_for_slide_with_logging(
    sales_data: pd.DataFrame,
    summary_instruction: str,
    slide_key: str,
    summarizer_agent: SummarizerAgent,
    agent_query: str
) -> str:
    """Generate summary text with logging."""
    try:
        # Use direct utility function for summary generation (more reliable for structured workflow)
        summary_text = generate_summary(sales_data, summary_instruction)
        
        logger.info(f"[SUMMARY GENERATION] Summary length: {len(summary_text)} characters")
        logger.info(f"[SUMMARY GENERATION] Summary preview: {summary_text[:200]}...")
        
        logger.info(f"  ✓ Summary generated for {slide_key} ({len(summary_text)} chars)")
        return summary_text
        
    except Exception as e:
        logger.error(f"  ✗ Error generating summary for {slide_key}: {str(e)}")
        # Try fallback: use agent if utility function fails
        try:
            logger.info(f"  Attempting fallback to summarizer agent for {slide_key}...")
            summary_result = asyncio.run(summarizer_agent.invoke(agent_query))
            logger.info(f"[LLM RESPONSE] Summarizer Agent Response:\n{_format_agent_response(summary_result)}")
            # Extract summary text from agent result if available
            if summary_result.get('success'):
                summary_content = summary_result.get('summary', {})
                if isinstance(summary_content, dict):
                    return summary_content.get('summary_text', '')
                return str(summary_content)
        except Exception as fallback_error:
            logger.error(f"  Fallback to agent also failed: {str(fallback_error)}")
        
        # Return default summary
        return f"• Analysis for {slide_key}\n• Data insights generated"

