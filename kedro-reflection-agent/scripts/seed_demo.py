#!/usr/bin/env python
"""Reset the demo back to its initial seed state.

Restores:
  - data/campaign/prompts/system_prompt.json  (weak v1 prompt)
  - data/campaign/skills/b2b_email_style.md   (weak v1 skill)
  - data/evaluation/eval_cases.json            (base 20 eval cases)

Clears:
  - data/outputs/runs/
  - data/outputs/reflections/
  - data/outputs/apply_history.json (if present)
  - data/demo_state.json

Run from the project root:
    python scripts/seed_demo.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Seed content — edit these if you want to change the "v1" baseline
# ---------------------------------------------------------------------------

SEED_SYSTEM_PROMPT: list[dict] = [
    {
        "role": "system",
        "content": "You are a B2B outreach email writer. Apply this style guide:\n\n{skill}",
    },
    {
        "role": "human",
        "content": "Write an outreach email to this customer about this product.\n\nCustomer:\n{customer}\n\nProduct:\n{product}",
    },
]

SEED_SKILL = """\
# B2B email style

- Be professional.
- Mention the product.
- End with a call to action.
"""

SEED_EVAL_CASES: list[dict] = [
    {
        "id": "case_001",
        "input": {"customer_id": "cust_002", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: logistics",
                    "company_size: mid",
                    "current_products: SD-WAN Basic (upsell context)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "made-up metrics"],
                "expected_cta": "meeting",
                "expected_tone": "consultative",
                "notes": "Upsell from SD-WAN Basic to Pro. Acknowledge the existing Basic tier and articulate the incremental value of Pro (centralized policy, application-aware shaping).",
            }
        },
    },
    {
        "id": "case_002",
        "input": {"customer_id": "cust_001", "product_id": "prod_005"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: retail",
                    "company_size: small",
                    "current_products: UC Suite Basic (upsell context)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "enterprise-only language"],
                "expected_cta": "demo",
                "expected_tone": "friendly",
                "notes": "Upsell from UC Basic to UC Pro for a small retail company. Email should be short, friendly, and emphasise the contact-centre and video features as a step up from telephony.",
            }
        },
    },
    {
        "id": "case_003",
        "input": {"customer_id": "cust_005", "product_id": "prod_002"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: manufacturing",
                    "company_size: enterprise",
                    "use case: shop-floor OT / AGV connectivity",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "claims unsupported by the product card"],
                "expected_cta": "meeting",
                "expected_tone": "consultative",
                "notes": "Strong fit. Email should connect 5G Private Network to a concrete manufacturing use case (e.g. AGVs, robotics) and reference their existing IoT Fleet investment.",
            }
        },
    },
    {
        "id": "case_004",
        "input": {"customer_id": "cust_009", "product_id": "prod_002"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: utilities",
                    "company_size: enterprise",
                    "use case: OT modernization / field connectivity",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "claims unsupported by the product card"],
                "expected_cta": "meeting",
                "expected_tone": "formal",
                "notes": "Strong fit for utilities OT. Email should reference grid/field operations and connect 5G Private Network to deterministic low-latency requirements.",
            }
        },
    },
    {
        "id": "case_005",
        "input": {"customer_id": "cust_002", "product_id": "prod_003"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: logistics",
                    "current_products: SD-WAN Basic, IoT Fleet (cross-sell context)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "call",
                "expected_tone": "consultative",
                "notes": "Cross-sell to existing customer with SD-WAN + IoT. Email should articulate how Managed Cloud Connect complements their current stack (warehouse management, telemetry ingestion).",
            }
        },
    },
    {
        "id": "case_006",
        "input": {"customer_id": "cust_004", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: retail",
                    "company_size: mid",
                    "multi-site context (stores)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "demo",
                "expected_tone": "consultative",
                "notes": "Mid retailer with multiple stores - good SD-WAN fit. Email should reference store-to-HQ connectivity and POS reliability.",
            }
        },
    },
    {
        "id": "case_007",
        "input": {"customer_id": "cust_006", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: healthcare",
                    "company_size: mid",
                    "current_products: Managed Cloud Connect (complementary positioning)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "regulated-data claims unsupported by product card"],
                "expected_cta": "meeting",
                "expected_tone": "formal",
                "notes": "Healthcare buyer with cloud connect already - SD-WAN positions as the underlay. Email should be formal and avoid unsupported compliance claims.",
            }
        },
    },
    {
        "id": "case_008",
        "input": {"customer_id": "cust_007", "product_id": "prod_003"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: media",
                    "company_size: mid",
                    "use case: production / asset workflows to cloud",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "demo",
                "expected_tone": "consultative",
                "notes": "Media mid-market with cloud-heavy workflows. Email should connect Managed Cloud Connect to post-production / content distribution use cases.",
            }
        },
    },
    {
        "id": "case_009",
        "input": {"customer_id": "cust_003", "product_id": "prod_002"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: banking",
                    "company_size: enterprise",
                    "explicit justification for 5G Private in a banking context",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic 5G hype with no use case"],
                "expected_cta": "meeting",
                "expected_tone": "formal",
                "notes": "Ambiguous fit. If pitching 5G Private to a bank, email must justify the use case (branch resilience, on-prem trading floor, secure campus) - not just describe the product.",
            }
        },
    },
    {
        "id": "case_010",
        "input": {"customer_id": "cust_003", "product_id": "prod_004"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: banking",
                    "specific banking IoT use case (ATMs, vehicles, branch sensors) or honest acknowledgement of limited fit",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic IoT hype with no banking-specific use case"],
                "expected_cta": "call",
                "expected_tone": "consultative",
                "notes": "Weak fit. A good email would either ground IoT Fleet in a banking-specific use case (ATM telemetry, secure logistics) or be deliberately exploratory rather than overselling.",
            }
        },
    },
    {
        "id": "case_011",
        "input": {"customer_id": "cust_006", "product_id": "prod_004"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: healthcare",
                    "use case: medical-device fleet or vehicle fleet",
                    "company_size: mid",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "regulated-data claims unsupported by product card"],
                "expected_cta": "call",
                "expected_tone": "consultative",
                "notes": "Unusual fit. Healthcare IoT could mean connected medical devices or ambulance fleets. Email should explicitly name a use case rather than describing the product generically.",
            }
        },
    },
    {
        "id": "case_012",
        "input": {"customer_id": "cust_010", "product_id": "prod_003"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: banking",
                    "company_size: small",
                    "starter-tier positioning for a small fintech",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "enterprise-only language"],
                "expected_cta": "demo",
                "expected_tone": "friendly",
                "notes": "Small fintech, no current products. Email should be friendly, acknowledge they are early stage, and pitch Managed Cloud Connect as a foundational layer rather than as an enterprise overhaul.",
            }
        },
    },
    {
        "id": "case_013",
        "input": {"customer_id": "cust_001", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "company_size: small (45 employees)",
                    "honest framing: SD-WAN Pro is enterprise-tier, may not fit",
                    "alternative or starter recommendation",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "treating a 45-person retailer as enterprise"],
                "expected_cta": "reply",
                "expected_tone": "friendly",
                "notes": "Mismatch. A 45-person retail company doesn't need premium SD-WAN. A good email either acknowledges the size mismatch and offers a fit-check conversation, or doesn't push the product.",
            }
        },
    },
    {
        "id": "case_014",
        "input": {"customer_id": "cust_008", "product_id": "prod_002"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "company_size: small (90 employees)",
                    "tenure: 0.5 years (new customer)",
                    "honest framing: 5G Private is enterprise-tier",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "overstating fit"],
                "expected_cta": "reply",
                "expected_tone": "friendly",
                "notes": "Clear mismatch. New small-business customer pitched a premium enterprise product. The email should acknowledge the mismatch or focus on discovery rather than hard-selling.",
            }
        },
    },
    {
        "id": "case_015",
        "input": {"customer_id": "cust_010", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "company_size: small",
                    "no SD-WAN need at this size unless multi-site",
                    "discovery-first framing",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "assuming multi-site without basis"],
                "expected_cta": "reply",
                "expected_tone": "friendly",
                "notes": "Mismatch. Small fintech doesn't typically need premium SD-WAN. The email should be exploratory and gated on whether they are multi-site.",
            }
        },
    },
    {
        "id": "case_016",
        "input": {"customer_id": "cust_008", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "company_size: small",
                    "tenure: 0.5 years",
                    "honest framing: SD-WAN Pro is enterprise-tier",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "overstating fit"],
                "expected_cta": "reply",
                "expected_tone": "friendly",
                "notes": "Mismatch. Small new logistics customer pitched premium SD-WAN. Email should be exploratory or acknowledge the size mismatch.",
            }
        },
    },
    {
        "id": "case_017",
        "input": {"customer_id": "cust_005", "product_id": "prod_003"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: manufacturing",
                    "company_size: enterprise",
                    "current_products: SD-WAN Pro, IoT Fleet (complementary positioning)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "meeting",
                "expected_tone": "consultative",
                "notes": "Cross-sell to existing enterprise customer. Email should connect Managed Cloud Connect to MES/ERP cloud workloads and reference their existing connectivity products.",
            }
        },
    },
    {
        "id": "case_018",
        "input": {"customer_id": "cust_004", "product_id": "prod_004"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: retail",
                    "use case: store-level IoT (inventory, refrigeration, fleet for distribution)",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage", "generic IoT hype with no retail use case"],
                "expected_cta": "demo",
                "expected_tone": "consultative",
                "notes": "Retail IoT angle. Email should ground IoT Fleet Connectivity in a concrete retail use case (delivery vans, refrigeration monitoring, store sensors).",
            }
        },
    },
    {
        "id": "case_019",
        "input": {"customer_id": "cust_007", "product_id": "prod_001"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: media",
                    "company_size: mid (260 employees)",
                    "use case: large file transfers / multi-location production",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "demo",
                "expected_tone": "consultative",
                "notes": "Mid media company - SD-WAN fits if they have multiple production sites or heavy cloud workflows. Email should justify the fit on workflow grounds, not company size alone.",
            }
        },
    },
    {
        "id": "case_020",
        "input": {"customer_id": "cust_009", "product_id": "prod_005"},
        "expected_output": {
            "rubric": {
                "required_mentions": [
                    "industry: utilities",
                    "company_size: enterprise",
                    "use case: field-workforce communications or contact-centre for customer support",
                ],
                "forbidden_mentions": ["fake SKU", "specific discount percentage"],
                "expected_cta": "meeting",
                "expected_tone": "formal",
                "notes": "Cross-sell UC to a utilities enterprise without current UC. Email should ground the pitch in a specific use case (dispatch, field-workforce, customer contact-centre) rather than generic UC features.",
            }
        },
    },
]


# ---------------------------------------------------------------------------
# Reset helpers
# ---------------------------------------------------------------------------

def _clear_outputs() -> None:
    """Delete all generated artefacts so the demo starts clean."""
    from datetime import datetime, timezone

    for folder in ["runs", "reflections"]:
        p = ROOT / "data" / "outputs" / folder
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
        (p / ".gitkeep").touch()

    # Write a fresh state file with a seed timestamp so the Streamlit UI
    # detects the reset and clears its @st.cache_data on the next render.
    demo_state = ROOT / "data" / "demo_state.json"
    seed_at = datetime.now(timezone.utc).isoformat()
    demo_state.write_text(
        json.dumps({"state": "idle", "seed_at": seed_at}, indent=2),
        encoding="utf-8",
    )


def _restore_prompt() -> None:
    path = ROOT / "data" / "campaign" / "prompts" / "system_prompt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(SEED_SYSTEM_PROMPT, indent=2), encoding="utf-8")
    print(f"  restored {path.relative_to(ROOT)}")


def _restore_skill() -> None:
    path = ROOT / "data" / "campaign" / "skills" / "b2b_email_style.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SEED_SKILL, encoding="utf-8")
    print(f"  restored {path.relative_to(ROOT)}")


def _restore_eval_cases(n: int | None = None) -> None:
    cases = SEED_EVAL_CASES[:n] if n is not None else SEED_EVAL_CASES
    path = ROOT / "data" / "evaluation" / "eval_cases.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    print(f"  restored {path.relative_to(ROOT)} ({len(cases)} cases)")


def _restore_targets(n: int | None = None) -> None:
    # Derive targets from eval cases — they share case_id / customer_id / product_id.
    all_targets = [
        {
            "case_id": c["id"],
            "customer_id": c["input"]["customer_id"],
            "product_id": c["input"]["product_id"],
        }
        for c in SEED_EVAL_CASES
    ]
    targets = all_targets[:n] if n is not None else all_targets
    path = ROOT / "data" / "campaign" / "targets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(targets, indent=2), encoding="utf-8")
    print(f"  restored {path.relative_to(ROOT)} ({len(targets)} targets)")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Reset the demo to its seed state.")
    parser.add_argument(
        "--cases",
        type=int,
        default=None,
        metavar="N",
        help="Seed only the first N eval cases and campaign targets (default: all 20).",
    )
    args = parser.parse_args()

    n = args.cases
    if n is not None and not (1 <= n <= len(SEED_EVAL_CASES)):
        parser.error(f"--cases must be between 1 and {len(SEED_EVAL_CASES)}, got {n}")

    label = f"{n} cases" if n is not None else "all 20 cases"
    print(f"Resetting demo to seed state ({label})…")
    _clear_outputs()
    print("  cleared data/outputs/runs/, data/outputs/reflections/, demo_state.json (apply_history.json preserved)")
    _restore_prompt()
    _restore_skill()
    _restore_eval_cases(n)
    _restore_targets(n)
    print("Done. The demo is ready to run from Step 1.")


if __name__ == "__main__":
    main()
