"""B2B Sales seed models (data/b2b_sales/seed/)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CustomerProfile(BaseModel):
    """B2B account enrichment — FK: customer_id."""

    customer_id: str
    company_name: str
    industry: Literal["retail", "logistics", "banking", "manufacturing",
                      "healthcare", "media", "utilities"]
    company_size: Literal["small", "mid", "enterprise"]
    employee_count: int
    primary_contact_name: str
    primary_contact_role: str
    current_products: list[str]


class ProductDetails(BaseModel):
    """B2B solution enrichment — FK: product_id."""

    product_id: str
    target_segment: Literal["small", "mid", "enterprise", "any"]
    key_benefits: list[str]
    short_description: str
    use_cases: list[str]
