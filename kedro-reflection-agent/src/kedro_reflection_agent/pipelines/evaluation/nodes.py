"""Nodes for the ``evaluation`` pipeline.

Fetches traces from Langfuse, runs heuristic scorers (subject present, length,
no fake SKUs, CTA present) and an LLM-judge (writing quality, personalisation,
groundedness), then writes per-case and aggregate scores. Nodes will be added
in a later slice.
"""
