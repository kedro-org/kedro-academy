"""Customer Care seed models (data/customer_care/seed/)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CustomerProfile(BaseModel):
    """Care customer enrichment with open issue context — FK: customer_id."""

    customer_id: str
    account_type: Literal["prepaid", "postpaid", "business"]
    service_type: Literal["mobile", "broadband", "tv", "bundle"]
    issue_type: Literal["billing", "network", "device", "roaming",
                        "account", "cancellation"]
    issue_description: str
    sentiment: Literal["frustrated", "upset", "neutral"]
    previous_contact_attempts: int


class ProductDetails(BaseModel):
    """Service resolution guide — FK: product_id."""

    product_id: str
    service_type: Literal["mobile", "broadband", "tv", "bundle"]
    known_issues: list[str]
    resolution_steps: list[str]
    compensation_policy: str
    escalation_triggers: list[str]
