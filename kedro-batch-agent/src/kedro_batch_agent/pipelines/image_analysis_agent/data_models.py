from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DamageAssessment(BaseModel):
    severity: str = Field(
        ...,
        description="Severity of the damage - must be one of 'minor', 'moderate', 'severe'",
    )
    estimated_cost: Optional[float] = Field(
        None, description="Estimated cost of the damage in USD"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in this assessment, from 0 to 1"
    )
    rationale: str = Field(..., description="Rationale behind the damage assessment")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        vs = v.strip().lower()
        if vs not in {"minor", "moderate", "severe"}:
            raise ValueError("Invalid severity level")
        return vs
