"""Agent tools for CrewAI agents in screening pipeline.

Tool builder functions for llm_context_node.
These functions take datasets as inputs and return tool objects.

Following CrewAI tool conventions from:
https://docs.crewai.com/en/learn/create-custom-tools
"""

from typing import Any

from crewai.tools import tool


def build_requirements_matcher_tool(
    normalized_job_posting: dict[str, Any],
    evidence_snippets: list[dict[str, Any]],
    matching_config: dict[str, Any],
) -> Any:
    """Build requirements matcher tool from datasets.

    Args:
        normalized_job_posting: Normalized job posting data
        evidence_snippets: List of evidence snippets
        matching_config: Matching configuration with parameters

    Returns:
        CrewAI tool object
    """
    job_requirements = normalized_job_posting.get("requirements", {})
    
    # Extract matching parameters from config
    min_word_length = matching_config.get("min_word_length", 3)
    confidence_config = matching_config.get("confidence", {})
    
    must_have_conf = confidence_config.get("must_have", {})
    must_have_base = must_have_conf.get("base", 0.5)
    must_have_increment = must_have_conf.get("increment", 0.1)
    must_have_max = must_have_conf.get("max", 0.9)
    
    nice_to_have_conf = confidence_config.get("nice_to_have", {})
    nice_to_have_base = nice_to_have_conf.get("base", 0.4)
    nice_to_have_increment = nice_to_have_conf.get("increment", 0.1)
    nice_to_have_max = nice_to_have_conf.get("max", 0.8)

    @tool("Requirements Matcher")
    def requirements_matcher_tool() -> list[dict[str, Any]]:
        """Match job requirements to evidence snippets from candidate profile.

        This tool performs evidence-based matching of job must-have and nice-to-have
        requirements to candidate evidence snippets. It returns match results with
        confidence scores and snippet IDs.

        Returns:
            List of match results with requirement, snippet_ids, and confidence
        """
        matches: list[dict[str, Any]] = []
        must_have = job_requirements.get("must_have", [])
        nice_to_have = job_requirements.get("nice_to_have", [])

        # Match must-have requirements
        for req in must_have:
            matching_snippets = []
            for snippet in evidence_snippets:
                snippet_text = snippet.get("text", "").lower()
                req_lower = req.lower()
                # Simple keyword matching (in production, use more sophisticated matching)
                if any(word in snippet_text for word in req_lower.split() if len(word) > min_word_length):
                    matching_snippets.append(snippet.get("snippet_id"))

            if matching_snippets:
                confidence = min(
                    must_have_max,
                    must_have_base + len(matching_snippets) * must_have_increment
                )
                matches.append({
                    "requirement": req,
                    "snippet_ids": matching_snippets,
                    "confidence": confidence,
                })

        # Match nice-to-have requirements
        for req in nice_to_have:
            matching_snippets = []
            for snippet in evidence_snippets:
                snippet_text = snippet.get("text", "").lower()
                req_lower = req.lower()
                if any(word in snippet_text for word in req_lower.split() if len(word) > min_word_length):
                    matching_snippets.append(snippet.get("snippet_id"))

            if matching_snippets:
                confidence = min(
                    nice_to_have_max,
                    nice_to_have_base + len(matching_snippets) * nice_to_have_increment
                )
                matches.append({
                    "requirement": req,
                    "snippet_ids": matching_snippets,
                    "confidence": confidence,
                })

        return matches

    return requirements_matcher_tool


def build_scoring_tool(
    normalized_job_posting: dict[str, Any],
    scoring_config: dict[str, Any],
) -> Any:
    """Build scoring tool from datasets.

    Args:
        normalized_job_posting: Normalized job posting data
        scoring_config: Scoring configuration with weights and bounds

    Returns:
        CrewAI tool object
    """
    must_have_requirements = normalized_job_posting.get("requirements", {}).get("must_have", [])
    
    # Extract weights and bounds from config
    weights = scoring_config.get("weights", {})
    weight_must_have = weights.get("must_have_coverage", 0.7)
    weight_confidence = weights.get("avg_confidence", 0.3)
    
    bounds = scoring_config.get("bounds", {})
    match_score_bounds = bounds.get("match_score", {"min": 0.0, "max": 100.0})
    coverage_bounds = bounds.get("must_have_coverage", {"min": 0.0, "max": 1.0})

    @tool("Scoring Tool")
    def scoring_tool(
        match_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate weighted match score based on requirement matches.

        Args:
            match_results: List of match results from requirements_matcher

        Returns:
            Dictionary with match_score (0-100), must_have_coverage (0-1), and breakdown
        """
        must_have_matches = [
            m for m in match_results
            if m.get("requirement") in must_have_requirements
        ]

        must_have_coverage = (
            len(must_have_matches) / len(must_have_requirements)
            if must_have_requirements else 0.0
        )

        # Calculate overall match score using configurable weights
        avg_confidence = (
            sum(m.get("confidence", 0.0) for m in match_results) / len(match_results)
            if match_results else 0.0
        )

        match_score = (must_have_coverage * weight_must_have + avg_confidence * weight_confidence) * 100

        return {
            "match_score": min(match_score_bounds["max"], max(match_score_bounds["min"], match_score)),
            "must_have_coverage": min(coverage_bounds["max"], max(coverage_bounds["min"], must_have_coverage)),
            "must_have_matches": len(must_have_matches),
            "total_matches": len(match_results),
        }

    return scoring_tool


def build_policy_check_tool(policy_rules: dict[str, Any]) -> Any:
    """Build policy check tool with rules from dataset.

    Args:
        policy_rules: Policy rules dictionary from dataset

    Returns:
        CrewAI tool object
    """
    @tool("Policy Check")
    def policy_check_tool(
        email_draft: dict[str, Any],
        recommendation: str,
    ) -> dict[str, Any]:
        """Check email draft and recommendation against policy guardrails.

        Validates EEO compliance, language appropriateness, and prevents promises.

        Args:
            email_draft: Dictionary with subject and body
            recommendation: Recommendation string (proceed, review, reject)

        Returns:
            Dictionary with allowed (bool), warnings (list), and risk_flags (list)
        """
        warnings = []
        risk_flags = []
        allowed = True

        email_body = email_draft.get("body", "").lower()
        email_subject = email_draft.get("subject", "").lower()

        # Check for inappropriate language
        inappropriate_words = policy_rules.get("inappropriate_words", [])
        for word in inappropriate_words:
            if word.lower() in email_body or word.lower() in email_subject:
                warnings.append(f"Potential promise detected: '{word}'")
                risk_flags.append(f"Language concern: {word}")

        # Check for EEO violations
        protected_classes = policy_rules.get("protected_classes", [])
        for term in protected_classes:
            if term.lower() in email_body:
                warnings.append(f"Potential EEO concern: reference to {term}")
                risk_flags.append(f"EEO concern: {term}")

        # Check recommendation consistency
        inconsistency_checks = policy_rules.get("inconsistency_checks", [])
        for check in inconsistency_checks:
            pattern = check.get("pattern", "").lower()
            when_recommendation = check.get("when_recommendation", "").lower()
            message = check.get("message", "Inconsistent messaging detected")
            
            if recommendation.lower() == when_recommendation and pattern in email_body:
                warnings.append(message)
                risk_flags.append("Message inconsistency")

        if risk_flags:
            allowed = False

        return {
            "allowed": allowed,
            "warnings": warnings,
            "risk_flags": risk_flags,
        }

    return policy_check_tool


def build_email_draft_tool(email_templates: dict[str, Any]) -> Any:
    """Build email draft tool with templates from prompt dataset.

    Args:
        email_templates: Email templates dictionary from prompt dataset

    Returns:
        CrewAI tool object
    """
    @tool("Email Draft Tool")
    def email_draft_tool(
        recommendation: str,
        candidate_name: str,
        job_title: str,
        next_steps: list[str],
    ) -> dict[str, Any]:
        """Draft email communication based on recommendation.

        This is a draft-only tool. Emails should never be sent without HR approval.

        Args:
            recommendation: Recommendation (proceed, review, reject)
            candidate_name: Candidate's name
            job_title: Job title
            next_steps: List of next steps or suggestions

        Returns:
            Dictionary with subject, body, and placeholders
        """
        # Get template for the recommendation type, default to review if not found
        recommendation_key = recommendation.lower()
        template = email_templates.get(recommendation_key, email_templates.get("review", {}))

        # Format next steps as a bulleted list
        next_steps_list = "\n".join(f"- {step}" for step in next_steps) if next_steps else ""

        # Replace placeholders in template
        subject_template = template.get("subject", "Application Update: {job_title}")
        body_template = template.get("body", "")

        subject = subject_template.format(
            candidate_name=candidate_name,
            job_title=job_title,
            next_steps_list=next_steps_list,
        )

        body = body_template.format(
            candidate_name=candidate_name,
            job_title=job_title,
            next_steps_list=next_steps_list,
        )

        return {
            "subject": subject,
            "body": body,
            "placeholders": {
                "candidate_name": candidate_name,
                "job_title": job_title,
            },
        }

    return email_draft_tool
