"""Pydantic models for structured agent output.

These models define the expected output structure from agents,
enabling AutoGen to return validated, typed responses instead
of raw text that requires manual parsing.
"""
from pydantic import BaseModel, Field


class ChartOutput(BaseModel):
    """Structured output for chart generation agents."""
    chart_path: str = Field(default="", description="File path to the generated chart image")
    status: str = Field(default="success", description="Status of chart generation")


class SummaryOutput(BaseModel):
    """Structured output for summary generation agents."""
    summary_text: str = Field(default="", description="Generated summary text with bullet points")
    status: str = Field(default="success", description="Status of summary generation")


class PlanOutput(BaseModel):
    """Structured output for planner agents."""
    plan: str = Field(default="", description="The generated plan for slide creation")
    status: str = Field(default="success", description="Status of planning")


class QAFeedbackOutput(BaseModel):
    """Structured output for critic/QA agents."""
    feedback: str = Field(default="", description="Quality feedback on the slide content")
    overall_score: float = Field(default=8.0, description="Quality score from 0-10")
    status: str = Field(default="success", description="Status of QA review")
