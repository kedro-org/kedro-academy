from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ClaimCause(str, Enum):
    """Enum for valid claim causes."""

    COLLISION = "collision"
    THEFT = "theft"
    FIRE = "fire"
    FLOOD = "flood"
    VANDALISM = "vandalism"
    HAIL = "hail"
    LIABILITY = "liability"


class User(BaseModel):
    """User information model."""

    name: Optional[str] = Field(..., description="Name of the user")
    user_id: Optional[str] = Field(..., description="Unique identifier for the user")


class Claim(BaseModel):
    """Insurance claim model."""

    policy_number: Optional[str] = Field(
        ..., description="Unique identifier for the policy"
    )
    user: Optional[User] = Field(
        ..., description="User information related to the claim"
    )
    cause: Optional[ClaimCause] = Field(
        ..., description="Cause of the claim - must be one of the predefined values"
    )
    date: Optional[str] = Field(..., description="Date of the claim")
    amount: Optional[float] = Field(..., description="Amount claimed")
