#!/usr/bin/env python
"""Reset the demo back to its baseline seed state.

Restores per-agent prompts, skills, eval cases, and targets.
Clears per-agent run outputs (runs/, reflections/).
Preserves apply_history.json and signal_index.json across resets.

Usage:
    python scripts/seed_demo.py               # seed all agents, all cases
    python scripts/seed_demo.py --cases 5     # limit each agent to 5 cases
    python scripts/seed_demo.py --agent b2b_sales   # one agent only

Make shortcut:
    make seed          # all agents, all cases
    make seed N=5      # all agents, 5 cases each
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from kedro_reflection_agent.utils.id_service import dataset_item_id

ROOT = Path(__file__).parent.parent

AGENTS = ["b2b_sales", "consumer_mktg", "customer_care"]

# ---------------------------------------------------------------------------
# Baseline prompts and skills
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS: dict[str, list[dict]] = {
    "b2b_sales": [
        {
            "role": "system",
            "content": "You are a B2B outreach email writer. Apply this style guide:\n\n{skill}",
        },
        {
            "role": "human",
            "content": "Write an outreach email to this customer about this product.\n\nCustomer:\n{customer}\n\nProduct:\n{product}",
        },
    ],
    "consumer_mktg": [
        {
            "role": "system",
            "content": "You are a telco consumer marketing specialist. Apply this tone and messaging guide:\n\n{skill}",
        },
        {
            "role": "human",
            "content": "Write a personalised upgrade offer message for this subscriber.\n\nSubscriber:\n{customer}\n\nOffer:\n{product}",
        },
    ],
    "customer_care": [
        {
            "role": "system",
            "content": "You are a telco customer care agent. Apply this tone and policy guide:\n\n{skill}",
        },
        {
            "role": "human",
            "content": "Write an empathetic support reply for this customer issue.\n\nCustomer:\n{customer}\n\nAffected service:\n{product}",
        },
    ],
}

SKILLS: dict[str, str] = {
    "b2b_sales": """\
# B2B email style

- Be professional.
- Mention the product.
- End with a call to action.
""",
    "consumer_mktg": """\
# Consumer marketing message style

- Be professional.
- Reference the subscriber's current plan or device.
- Highlight the specific benefit relevant to their usage.
- End with a clear, single call to action.
- Keep tone friendly and benefit-led, not pushy.
""",
    "customer_care": """\
# Customer care reply style

- Be professional.
- Open by acknowledging the customer's specific issue.
- State clearly what action you are taking to resolve it.
- Give one concrete next step.
- Never promise what cannot be delivered.
- Close warmly and invite follow-up.
""",
}

# ---------------------------------------------------------------------------
# Eval cases — source of truth for both eval_cases.json and targets.json
# ---------------------------------------------------------------------------

EVAL_CASES: dict[str, list[dict]] = {
    "b2b_sales": [
        {
            "id": "case_001",
            "input": {"customer_id": "cust_002", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: logistics", "company_size: mid", "current_products: SD-WAN Basic (upsell context)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "made-up metrics"],
                    "expected_cta": "meeting",
                    "expected_tone": "consultative",
                    "notes": "Upsell from SD-WAN Basic to Pro. Acknowledge the existing Basic tier and articulate the incremental value of Pro.",
                }
            },
        },
        {
            "id": "case_002",
            "input": {"customer_id": "cust_001", "product_id": "prod_005"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: retail", "company_size: small", "current_products: UC Suite Basic (upsell context)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "enterprise-only language"],
                    "expected_cta": "demo",
                    "expected_tone": "friendly",
                    "notes": "Upsell from UC Basic to UC Pro for a small retail company. Short, friendly, emphasise contact-centre and video features.",
                }
            },
        },
        {
            "id": "case_003",
            "input": {"customer_id": "cust_005", "product_id": "prod_002"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: manufacturing", "company_size: enterprise", "use case: shop-floor OT / AGV connectivity"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "claims unsupported by the product card"],
                    "expected_cta": "meeting",
                    "expected_tone": "consultative",
                    "notes": "Strong fit. Connect 5G Private Network to a concrete manufacturing use case (AGVs, robotics) and reference their existing IoT Fleet investment.",
                }
            },
        },
        {
            "id": "case_004",
            "input": {"customer_id": "cust_009", "product_id": "prod_002"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: utilities", "company_size: enterprise", "use case: OT modernization / field connectivity"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "claims unsupported by product card"],
                    "expected_cta": "meeting",
                    "expected_tone": "formal",
                    "notes": "Strong fit for utilities OT. Reference grid/field operations and connect 5G Private Network to deterministic low-latency requirements.",
                }
            },
        },
        {
            "id": "case_005",
            "input": {"customer_id": "cust_002", "product_id": "prod_003"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: logistics", "current_products: SD-WAN Basic, IoT Fleet (cross-sell context)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "call",
                    "expected_tone": "consultative",
                    "notes": "Cross-sell to existing customer with SD-WAN + IoT. Connect Managed Cloud Connect to warehouse management and telemetry ingestion.",
                }
            },
        },
        {
            "id": "case_006",
            "input": {"customer_id": "cust_004", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: retail", "company_size: mid", "multi-site context (stores)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "demo",
                    "expected_tone": "consultative",
                    "notes": "Mid retailer with multiple stores — SD-WAN fit. Reference store-to-HQ connectivity and POS reliability.",
                }
            },
        },
        {
            "id": "case_007",
            "input": {"customer_id": "cust_006", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: healthcare", "company_size: mid", "current_products: Managed Cloud Connect (complementary positioning)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "regulated-data claims unsupported by product card"],
                    "expected_cta": "meeting",
                    "expected_tone": "formal",
                    "notes": "Healthcare buyer with cloud connect already — SD-WAN as the underlay. Formal tone; avoid unsupported compliance claims.",
                }
            },
        },
        {
            "id": "case_008",
            "input": {"customer_id": "cust_007", "product_id": "prod_003"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: media", "company_size: mid", "use case: production / asset workflows to cloud"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "demo",
                    "expected_tone": "consultative",
                    "notes": "Media mid-market with cloud-heavy workflows. Connect Managed Cloud Connect to post-production / content distribution use cases.",
                }
            },
        },
        {
            "id": "case_009",
            "input": {"customer_id": "cust_003", "product_id": "prod_002"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: banking", "company_size: enterprise", "explicit justification for 5G Private in a banking context"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic 5G hype with no use case"],
                    "expected_cta": "meeting",
                    "expected_tone": "formal",
                    "notes": "Ambiguous fit. Must justify the use case (branch resilience, trading floor, secure campus) — not just describe the product.",
                }
            },
        },
        {
            "id": "case_010",
            "input": {"customer_id": "cust_003", "product_id": "prod_004"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: banking", "specific banking IoT use case (ATMs, vehicles, branch sensors) or honest acknowledgement of limited fit"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic IoT hype with no banking-specific use case"],
                    "expected_cta": "call",
                    "expected_tone": "consultative",
                    "notes": "Weak fit. Ground IoT Fleet in a banking-specific use case or be exploratory rather than overselling.",
                }
            },
        },
        {
            "id": "case_011",
            "input": {"customer_id": "cust_006", "product_id": "prod_004"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: healthcare", "use case: medical-device fleet or vehicle fleet", "company_size: mid"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "regulated-data claims unsupported by product card"],
                    "expected_cta": "call",
                    "expected_tone": "consultative",
                    "notes": "Healthcare IoT — name a use case (connected medical devices, ambulance fleets) rather than describing the product generically.",
                }
            },
        },
        {
            "id": "case_012",
            "input": {"customer_id": "cust_010", "product_id": "prod_003"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: banking", "company_size: small", "starter-tier positioning for a small fintech"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "enterprise-only language"],
                    "expected_cta": "demo",
                    "expected_tone": "friendly",
                    "notes": "Small fintech, no current products. Friendly, foundational pitch — not an enterprise overhaul.",
                }
            },
        },
        {
            "id": "case_013",
            "input": {"customer_id": "cust_001", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["company_size: small (45 employees)", "honest framing: SD-WAN Pro is enterprise-tier, may not fit", "alternative or starter recommendation"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "treating a 45-person retailer as enterprise"],
                    "expected_cta": "reply",
                    "expected_tone": "friendly",
                    "notes": "Mismatch. Acknowledge size mismatch; offer a fit-check conversation rather than hard selling.",
                }
            },
        },
        {
            "id": "case_014",
            "input": {"customer_id": "cust_008", "product_id": "prod_002"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["company_size: small (90 employees)", "tenure: 0.5 years (new customer)", "honest framing: 5G Private is enterprise-tier"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "overstating fit"],
                    "expected_cta": "reply",
                    "expected_tone": "friendly",
                    "notes": "Clear mismatch. New small-business customer — focus on discovery rather than hard-selling.",
                }
            },
        },
        {
            "id": "case_015",
            "input": {"customer_id": "cust_010", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["company_size: small", "no SD-WAN need at this size unless multi-site", "discovery-first framing"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "assuming multi-site without basis"],
                    "expected_cta": "reply",
                    "expected_tone": "friendly",
                    "notes": "Mismatch. Exploratory and gated on whether they are multi-site.",
                }
            },
        },
        {
            "id": "case_016",
            "input": {"customer_id": "cust_008", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["company_size: small", "tenure: 0.5 years", "honest framing: SD-WAN Pro is enterprise-tier"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "overstating fit"],
                    "expected_cta": "reply",
                    "expected_tone": "friendly",
                    "notes": "Mismatch. Small new logistics customer — exploratory or acknowledge the size mismatch.",
                }
            },
        },
        {
            "id": "case_017",
            "input": {"customer_id": "cust_005", "product_id": "prod_003"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: manufacturing", "company_size: enterprise", "current_products: SD-WAN Pro, IoT Fleet (complementary positioning)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "meeting",
                    "expected_tone": "consultative",
                    "notes": "Cross-sell to existing enterprise customer. Connect Managed Cloud Connect to MES/ERP cloud workloads.",
                }
            },
        },
        {
            "id": "case_018",
            "input": {"customer_id": "cust_004", "product_id": "prod_004"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: retail", "use case: store-level IoT (inventory, refrigeration, fleet for distribution)"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic IoT hype with no retail use case"],
                    "expected_cta": "demo",
                    "expected_tone": "consultative",
                    "notes": "Retail IoT — ground in a concrete retail use case (delivery vans, refrigeration monitoring, store sensors).",
                }
            },
        },
        {
            "id": "case_019",
            "input": {"customer_id": "cust_007", "product_id": "prod_001"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: media", "company_size: mid (260 employees)", "use case: large file transfers / multi-location production"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "demo",
                    "expected_tone": "consultative",
                    "notes": "Mid media company — justify SD-WAN fit on workflow grounds, not company size alone.",
                }
            },
        },
        {
            "id": "case_020",
            "input": {"customer_id": "cust_009", "product_id": "prod_005"},
            "expected_output": {
                "rubric": {
                    "required_mentions": ["industry: utilities", "company_size: enterprise", "use case: field-workforce communications or contact-centre"],
                    "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                    "expected_cta": "meeting",
                    "expected_tone": "formal",
                    "notes": "Cross-sell UC to utilities enterprise. Ground in a specific use case (dispatch, field-workforce, customer contact-centre).",
                }
            },
        },
    ],
    "consumer_mktg": [
        {
            "id": "case_001",
            "input": {"customer_id": "cust_011", "product_id": "prod_011"},
            "expected_output": {"rubric": {"required_mentions": ["current usage near data limit", "iPhone upgrade benefit", "trade-in or monthly plan"], "forbidden_mentions": ["fake pricing", "guaranteed coverage claims", "made-up specs"], "expected_cta": "trial", "expected_tone": "friendly", "notes": "Premium subscriber already on Unlimited — pitch iPhone 15 Pro on device plan. Must reference their existing plan and offer upgrade path, not sell them data."}},
        },
        {
            "id": "case_002",
            "input": {"customer_id": "cust_012", "product_id": "prod_006"},
            "expected_output": {"rubric": {"required_mentions": ["current Essential 20GB plan", "data usage approaching limit", "Unlimited 5G benefit"], "forbidden_mentions": ["fake pricing", "guaranteed 5G everywhere", "unnecessary urgency"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Budget subscriber on Essential 20GB — upgrade to Unlimited 5G. Reference current plan and explain benefit of removing the cap."}},
        },
        {
            "id": "case_003",
            "input": {"customer_id": "cust_013", "product_id": "prod_012"},
            "expected_output": {"rubric": {"required_mentions": ["Family Bundle context", "Samsung Galaxy S24 features", "monthly plan option"], "forbidden_mentions": ["fake pricing", "guaranteed delivery dates", "made-up specs"], "expected_cta": "demo", "expected_tone": "friendly", "notes": "Mid segment Family Bundle subscriber — pitch Samsung Galaxy S24. Connect family usage to device upgrade."}},
        },
        {
            "id": "case_004",
            "input": {"customer_id": "cust_014", "product_id": "prod_007"},
            "expected_output": {"rubric": {"required_mentions": ["current Prepaid plan", "benefit of Essential 20GB contract", "no-contract or rolling option"], "forbidden_mentions": ["fake pricing", "lock-in language", "guaranteed speeds"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Budget Prepaid subscriber — step-up to Essential 20GB. Frame upgrade as flexible, not a lock-in."}},
        },
        {
            "id": "case_005",
            "input": {"customer_id": "cust_015", "product_id": "prod_015"},
            "expected_output": {"rubric": {"required_mentions": ["existing Unlimited 5G plan", "Apple Watch health features", "connectivity with iPhone"], "forbidden_mentions": ["fake pricing", "medical claims", "guaranteed battery life"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Premium Unlimited subscriber — cross-sell Apple Watch. Connect to health/lifestyle benefits and iPhone ecosystem."}},
        },
        {
            "id": "case_006",
            "input": {"customer_id": "cust_016", "product_id": "prod_006"},
            "expected_output": {"rubric": {"required_mentions": ["current Essential 20GB plan", "loyalty tenure of 5+ years", "Unlimited 5G value"], "forbidden_mentions": ["fake pricing", "guaranteed 5G everywhere", "pressure tactics"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Long-tenure budget subscriber — upgrade to Unlimited. Acknowledge loyalty and frame upgrade as a reward."}},
        },
        {
            "id": "case_007",
            "input": {"customer_id": "cust_017", "product_id": "prod_013"},
            "expected_output": {"rubric": {"required_mentions": ["Roaming Plus usage context", "iPad Pro business productivity", "connectivity on the go"], "forbidden_mentions": ["fake pricing", "guaranteed roaming coverage", "made-up performance claims"], "expected_cta": "demo", "expected_tone": "friendly", "notes": "Roaming Plus subscriber — cross-sell iPad Pro for travel productivity. Connect to their roaming lifestyle."}},
        },
        {
            "id": "case_008",
            "input": {"customer_id": "cust_018", "product_id": "prod_007"},
            "expected_output": {"rubric": {"required_mentions": ["current Prepaid Starter plan", "Essential 20GB benefit", "flexible 30-day option"], "forbidden_mentions": ["fake pricing", "lock-in language", "overpromising coverage"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "New budget subscriber on Prepaid — step-up to Essential 20GB. Warm and low-pressure."}},
        },
        {
            "id": "case_009",
            "input": {"customer_id": "cust_019", "product_id": "prod_011"},
            "expected_output": {"rubric": {"required_mentions": ["long tenure of 7+ years", "current Unlimited 5G plan", "iPhone 15 Pro upgrade benefit"], "forbidden_mentions": ["fake pricing", "false upgrade urgency", "made-up specs"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Long-tenure premium subscriber — pitch iPhone 15 Pro as loyalty reward. Acknowledge loyalty prominently."}},
        },
        {
            "id": "case_010",
            "input": {"customer_id": "cust_020", "product_id": "prod_008"},
            "expected_output": {"rubric": {"required_mentions": ["current Essential 20GB plan", "Family Bundle value", "per-line savings"], "forbidden_mentions": ["fake pricing", "assuming they have a family", "guaranteed savings claims"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Budget subscriber — pitch Family Bundle. Ask about household context; frame savings as conditional on having multiple users."}},
        },
    ],
    "customer_care": [
        {
            "id": "case_001",
            "input": {"customer_id": "cust_011", "product_id": "prod_006"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge billing error", "investigate or credit action", "apologise for inconvenience"], "forbidden_mentions": ["blame the customer", "deny the issue without checking", "fake reference numbers"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Billing dispute on Unlimited 5G. Apologise, confirm investigation, offer timeline."}},
        },
        {
            "id": "case_002",
            "input": {"customer_id": "cust_012", "product_id": "prod_007"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge signal issue", "network check or engineer visit", "timeline for resolution"], "forbidden_mentions": ["dismiss as device fault without checking", "promise specific fix date", "blame customer's location"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Network coverage issue. Offer a concrete next step; do not dismiss."}},
        },
        {
            "id": "case_003",
            "input": {"customer_id": "cust_013", "product_id": "prod_008"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge missing top-up credit", "check or restore credit action", "24-hour processing context"], "forbidden_mentions": ["claim top-up was not received", "ask customer to top up again without checking", "fake case numbers"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Top-up credit not appearing. Acknowledge, investigate, set expectations."}},
        },
        {
            "id": "case_004",
            "input": {"customer_id": "cust_014", "product_id": "prod_010"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge roaming charges despite add-on", "investigate or refund action", "confirm Roaming Plus coverage"], "forbidden_mentions": ["deny Roaming Plus covers Spain", "blame customer for not activating", "no concrete action"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Roaming charge dispute. Investigate and offer refund if confirmed; no blame shifting."}},
        },
        {
            "id": "case_005",
            "input": {"customer_id": "cust_015", "product_id": "prod_006"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge price increase", "retention offer or explanation of value", "no cancellation pressure"], "forbidden_mentions": ["dismiss the concern", "threaten contract terms", "deny the price increase"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Cancellation threat due to price increase. Empathetic; offer retention value without pressure."}},
        },
        {
            "id": "case_006",
            "input": {"customer_id": "cust_016", "product_id": "prod_007"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge wrong billing amount", "confirm plan change or refund action", "apologise for error"], "forbidden_mentions": ["claim plan was not changed", "ask customer to pay the wrong amount", "no concrete resolution"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Wrong plan charged after downgrade. Acknowledge error, confirm correct plan, offer credit."}},
        },
        {
            "id": "case_007",
            "input": {"customer_id": "cust_017", "product_id": "prod_009"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge call quality issue", "troubleshooting steps or escalation", "timeline or follow-up"], "forbidden_mentions": ["blame customer's device", "dismiss EC1 as a known blackspot without checking", "no next step"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Location-specific call issue. Acknowledge, offer diagnostics, commit to follow-up."}},
        },
        {
            "id": "case_008",
            "input": {"customer_id": "cust_018", "product_id": "prod_010"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge unexpected charge", "investigate porting fee legitimacy", "refund if error confirmed"], "forbidden_mentions": ["insist the charge is valid without checking", "ask customer to prove they did not request port", "no action"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Unexpected porting fee. Investigate and refund if not authorised."}},
        },
        {
            "id": "case_009",
            "input": {"customer_id": "cust_019", "product_id": "prod_008"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge checkout error", "alternative way to add line", "escalate if website fault persists"], "forbidden_mentions": ["blame the customer's browser", "say the product is unavailable", "no workaround offered"], "expected_cta": "call", "expected_tone": "friendly", "notes": "Website error adding 5th line. Offer alternative (phone, store); do not just say try again."}},
        },
        {
            "id": "case_010",
            "input": {"customer_id": "cust_020", "product_id": "prod_007"},
            "expected_output": {"rubric": {"required_mentions": ["acknowledge billing error", "credit or refund action", "confirm no port request was made"], "forbidden_mentions": ["claim porting fee is standard", "ask customer to pay the charge", "no concrete resolution"], "expected_cta": "reply", "expected_tone": "friendly", "notes": "Incorrect porting fee. Take dispute seriously; proactively offer a refund."}},
        },
    ],
}


# ---------------------------------------------------------------------------
# Langfuse prompt baselines (seeded locally; sync_policy:local means these
# are used directly without requiring the prompts to exist in Langfuse).
# ---------------------------------------------------------------------------

JUDGE_PROMPTS: dict[str, list[dict]] = {
    "b2b_sales": [
        {
            "role": "system",
            "content": (
                "You are a strict evaluator of B2B outreach emails. You score each email on three dimensions, each in the range 0.0 to 1.0.\n\n"
                "DIMENSIONS\n\n"
                "1. writing_quality\n"
                "   - Clarity, grammar, flow, professional tone.\n"
                "   - Does the tone match the rubric's `expected_tone`?\n"
                "   - Are there awkward phrasings, run-on sentences, jargon dumps?\n"
                "   - 1.0 = polished, on-tone, easy to read. 0.5 = readable but uneven. 0.0 = poor.\n\n"
                "2. personalization\n"
                "   - Does the email genuinely use the customer's industry, company_size, account_tenure_years, primary_contact_name/role, and especially `current_products`?\n"
                "   - Generic mentions of the company name only = low. Real tailoring (upsell context, role-relevant framing, tenure-aware tone) = high.\n"
                "   - Cross-check the rubric's `required_mentions` and `forbidden_mentions`. Missing any required mention or hitting any forbidden mention should hurt this score.\n"
                "   - 1.0 = the email could only have been written for this customer. 0.0 = could be sent to anyone.\n\n"
                "3. groundedness\n"
                "   - Does the email make ONLY claims supported by the product's `short_description` and `key_benefits`?\n"
                "   - Penalise hallucinated numbers, fake SKUs, made-up metrics, invented case studies, fabricated discounts.\n"
                "   - 1.0 = every factual claim is traceable to the product card. 0.0 = mostly hallucinated.\n\n"
                "For each dimension provide both:\n"
                "  - the score (a float between 0.0 and 1.0)\n"
                "  - a one-sentence reason citing the specific evidence (or lack of it) in the email.\n\n"
                "Be strict. Use the full range. Reserve 1.0 only for emails that genuinely earn it."
            ),
        },
        {
            "role": "human",
            "content": (
                "Evaluate this outreach email.\n\n"
                "Customer:\n{customer}\n\nProduct:\n{product}\n\n"
                "Rubric (what the email should achieve):\n{rubric}\n\n"
                "Email:\nSubject: {subject}\n\nBody:\n{body}"
            ),
        },
    ],
    "consumer_mktg": [
        {
            "role": "system",
            "content": (
                "You are a strict evaluator of consumer marketing messages for a telecom provider. Score each message on five dimensions, each 0.0–1.0.\n\n"
                "DIMENSIONS\n\n"
                "1. offer_relevance\n"
                "   - Does the offer match the subscriber's current plan, device, or usage pattern?\n"
                "   - Is the upgrade path logical (e.g. stepping up from Essential to Unlimited, not selling them something they already have)?\n"
                "   - 1.0 = offer is exactly right for this subscriber's situation. 0.0 = irrelevant or already owned.\n\n"
                "2. personalisation\n"
                "   - Does the message reference the subscriber's specific plan, tenure, usage, or device?\n"
                "   - Generic 'great news for you!' without subscriber data = low.\n"
                "   - 1.0 = message could only have been written for this subscriber. 0.0 = entirely generic.\n\n"
                "3. urgency_cta\n"
                "   - Is there a clear, single call to action?\n"
                "   - Is urgency present without being pushy or creating false scarcity?\n"
                "   - 1.0 = clear CTA matching rubric's expected_cta, appropriate urgency. 0.0 = no CTA or contradicts rubric.\n\n"
                "4. tone\n"
                "   - Is the tone friendly, warm, and benefit-led?\n"
                "   - Does it match the rubric's expected_tone?\n"
                "   - 1.0 = on-tone, engaging, non-pushy. 0.0 = off-tone, pressuring, or robotic.\n\n"
                "5. compliance\n"
                "   - Are all claims accurate? No fake pricing, no guaranteed coverage, no fabricated speeds or specs.\n"
                "   - Are forbidden_mentions from the rubric absent?\n"
                "   - 1.0 = fully accurate, no misleading claims. 0.0 = false or prohibited claims present.\n\n"
                "For each dimension provide the score and a one-sentence reason citing specific evidence.\n"
                "Be strict. Use the full range."
            ),
        },
        {
            "role": "human",
            "content": (
                "Evaluate this consumer marketing message.\n\n"
                "Subscriber:\n{customer}\n\nOffer:\n{product}\n\n"
                "Rubric (what the message should achieve):\n{rubric}\n\n"
                "Message:\nSubject: {subject}\n\nBody:\n{body}"
            ),
        },
    ],
    "customer_care": [
        {
            "role": "system",
            "content": (
                "You are a strict evaluator of customer care support replies for a telecom provider. Score each reply on five dimensions, each 0.0–1.0.\n\n"
                "DIMENSIONS\n\n"
                "1. empathy_opener\n"
                "   - Does the reply open by genuinely acknowledging the customer's specific issue?\n"
                "   - Generic 'Thank you for contacting us' without acknowledging the issue = low.\n"
                "   - 1.0 = opener is warm and specific to the customer's problem. 0.0 = dismissive or entirely generic.\n\n"
                "2. resolution_clarity\n"
                "   - Is the resolution path clear? Does the agent state what action is being taken?\n"
                "   - Is a concrete next step provided (timeline, callback, credit, fix)?\n"
                "   - 1.0 = clear resolution with concrete next step. 0.0 = vague, no action stated.\n\n"
                "3. tone\n"
                "   - Is the tone warm, professional, and non-defensive?\n"
                "   - Does it avoid blame-shifting or dismissing the customer?\n"
                "   - 1.0 = empathetic and professional throughout. 0.0 = cold, defensive, or blaming.\n\n"
                "4. compliance\n"
                "   - Does the reply avoid false promises, fake reference numbers, or claims unsupported by policy?\n"
                "   - Are forbidden_mentions from the rubric absent?\n"
                "   - 1.0 = fully compliant, no unsupported claims. 0.0 = false promises or prohibited content.\n\n"
                "5. escalation_avoidance\n"
                "   - Does the reply resolve or meaningfully progress the issue rather than prematurely escalating or asking the customer to try again?\n"
                "   - 1.0 = concrete resolution path, no unnecessary escalation. 0.0 = deflects or escalates without reason.\n\n"
                "For each dimension provide the score and a one-sentence reason citing specific evidence.\n"
                "Be strict. Use the full range."
            ),
        },
        {
            "role": "human",
            "content": (
                "Evaluate this customer care reply.\n\n"
                "Customer:\n{customer}\n\nAffected service:\n{product}\n\n"
                "Rubric (what the reply should achieve):\n{rubric}\n\n"
                "Reply:\nSubject: {subject}\n\nBody:\n{body}"
            ),
        },
    ],
}

_META_AGENT_SYSTEM = (
    "You are a reflection meta-agent for a {agent_label} generation system. "
    "Your job is to analyse evaluation failures and propose concrete, evidence-based improvements.\n\n"
    "You will receive:\n"
    "- The current system prompt, which contains a skill-injection placeholder where the style guide is inserted at runtime\n"
    "- The current skill file (markdown style guide)\n"
    "- Aggregate evaluation scores across all generated outputs\n"
    "- The worst-scoring cases: the outputs produced, per-scorer evaluator feedback, and the rubric that defined what the output should achieve\n\n"
    "Your task:\n"
    "1. Identify the dominant failure patterns across the worst cases — be specific and cite evaluator comments as evidence.\n"
    "2. Write a complete improved system prompt that directly addresses those failures. IMPORTANT: the current system prompt you receive contains a skill-injection placeholder; you must carry it over into your improved prompt exactly as written — do not rename, remove, or relocate it.\n"
    "3. Write a complete improved skill file (markdown) that reinforces the new prompt.\n"
    "4. Propose 2–3 new evaluation cases that target the exact failure modes you identified. Each new case must:\n"
    "   - Reuse a real customer_id and product_id from the worst-scoring cases you were shown.\n"
    "   - Include a precise rubric: required_mentions (list of strings), forbidden_mentions (list of strings), expected_cta (one of: meeting, demo, call, reply, trial), expected_tone (one of: formal, consultative, friendly), and notes explaining why this case specifically targets the failure mode.\n"
    "   - Use a case_id of the form 'regression_NNN' (e.g. regression_001).\n\n"
    "Every change must be traceable to a specific failure pattern in the data. Do not make changes unsupported by the evidence.\n\n"
    "Critical constraint — do NOT regress passing dimensions:\n"
    "Before proposing any change, examine the aggregate_scores_json and identify which "
    "dimensions are ALREADY above the passing_threshold. Those dimensions are working correctly "
    "and must be preserved. Your proposed prompt and skill changes must be surgical: fix the "
    "weakest dimensions without removing or diluting the instructions that currently support "
    "the strong ones. If a proposed change would risk regressing a passing dimension in order "
    "to fix a failing one, choose a more conservative additive approach instead — add guidance "
    "for the weak dimension rather than replacing guidance for the strong one."
)

_META_AGENT_HUMAN = (
    "Current system prompt:\n{current_prompt}\n\n"
    "Current skill file:\n{skill_text}\n\n"
    "Aggregate scores:\n{aggregate_scores_json}\n\n"
    "Worst-scoring cases (outputs, evaluator feedback, rubrics):\n{failing_cases_json}"
)

_AGENT_LABELS = {
    "b2b_sales": "B2B outreach email",
    "consumer_mktg": "consumer marketing message",
    "customer_care": "customer care support reply",
}

META_AGENT_PROMPTS: dict[str, list[dict]] = {
    agent: [
        {"role": "system", "content": _META_AGENT_SYSTEM.format(agent_label=label)},
        {"role": "human", "content": _META_AGENT_HUMAN},
    ]
    for agent, label in _AGENT_LABELS.items()
}


# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------

def _clear_outputs(agents: list[str]) -> None:
    from datetime import datetime, timezone

    for agent in agents:
        for folder in ["runs", "reflections"]:
            p = ROOT / "data" / agent / "outputs" / folder
            if p.exists():
                shutil.rmtree(p)
            p.mkdir(parents=True, exist_ok=True)
            (p / ".gitkeep").touch()

    # Clear cross-run and observability indexes so CLI and UI resets are identical
    outputs = ROOT / "data" / "outputs"
    for fname in ("run_index.json", "apply_history.json", "signal_index.json"):
        f = outputs / fname
        if f.exists():
            f.unlink()

    demo_state = ROOT / "data" / "demo_state.json"
    seed_at = datetime.now(timezone.utc).isoformat()
    demo_state.write_text(
        json.dumps({"state": "idle", "seed_at": seed_at}, indent=2),
        encoding="utf-8",
    )


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def _write_json_if_absent(path: Path, data: object) -> None:
    if path.exists():
        print(f"  kept  {path.relative_to(ROOT)}")
        return
    _write_json(path, data)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")


def _seed_agent(agent: str, n: int | None) -> None:
    print(f"\n[{agent}]")
    cases = EVAL_CASES[agent]
    if n is not None:
        cases = cases[:n]

    # Wipe directories that accumulate versioned/stale artifacts from the apply pipeline.
    # evaluation/prompts and reflection/prompts are NOT wiped — judge prompts and
    # meta-agent prompts are static evaluation infrastructure that must never be reset.
    for _dir in [
        ROOT / "data" / agent / "campaign" / "prompts",
        ROOT / "data" / agent / "campaign" / "skills",
    ]:
        if _dir.exists():
            shutil.rmtree(_dir)
        _dir.mkdir(parents=True, exist_ok=True)

    # Prompt + skill (weak v1 baseline)
    _write_json(ROOT / "data" / agent / "campaign" / "prompts" / "system_prompt.json", SYSTEM_PROMPTS[agent])
    _write_text(ROOT / "data" / agent / "campaign" / "skills" / f"{agent}_style.md", SKILLS[agent])

    # Seed judge and meta-agent prompts only on first run (never overwrite — they are
    # static evaluation infrastructure and must not change between reflection cycles).
    _write_json_if_absent(ROOT / "data" / agent / "evaluation" / "prompts" / "judge_prompt.json", JUDGE_PROMPTS[agent])
    _write_json_if_absent(ROOT / "data" / agent / "reflection" / "prompts" / "meta_agent_prompt.json", META_AGENT_PROMPTS[agent])

    # Targets — derived from eval cases; use logical case_id as the file key.
    targets = [
        {"case_id": c["id"], **c["input"]}
        for c in cases
    ]
    _write_json(ROOT / "data" / agent / "seed" / "targets.json", targets)

    # Eval cases — replace logical "id" with a deterministic UUID so that
    # item.id is always the same across Langfuse resets.  The logical case_id
    # is preserved in input["case_id"] so campaign_task can still find the
    # email file by its human-readable name (case_001.json).
    eval_cases = [
        {
            **c,
            "id": dataset_item_id(agent, c["id"]),
            "input": {**c["input"], "case_id": c["id"]},
        }
        for c in cases
    ]
    _write_json(ROOT / "data" / agent / "evaluation" / "eval_cases.json", eval_cases)

    label = f"{len(cases)} cases"
    print(f"  seeded {label}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reset the demo to its seed state.")
    parser.add_argument(
        "--cases",
        type=int,
        default=None,
        metavar="N",
        help="Seed only the first N eval cases and targets per agent (default: all).",
    )
    parser.add_argument(
        "--agent",
        choices=AGENTS,
        default=None,
        help="Seed a single agent only (default: all agents).",
    )
    args = parser.parse_args()

    agents = [args.agent] if args.agent else AGENTS

    max_cases = max(len(EVAL_CASES[a]) for a in agents)
    if args.cases is not None and not (1 <= args.cases <= max_cases):
        parser.error(f"--cases must be between 1 and {max_cases}, got {args.cases}")

    label = f"{args.cases} cases" if args.cases else "all cases"
    scope = args.agent or "all agents"
    print(f"Resetting demo — {scope}, {label}…")

    _clear_outputs(agents)
    print(f"  cleared outputs for: {', '.join(agents)}")

    for agent in agents:
        _seed_agent(agent, args.cases)

    print("\nDone. Run: kedro run --params \"agent_id=b2b_sales,run_id=run_1\"")


if __name__ == "__main__":
    main()
