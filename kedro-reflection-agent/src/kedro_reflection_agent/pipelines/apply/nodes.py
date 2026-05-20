"""Nodes for the ``apply`` pipeline.

Applies an approved reflection proposal:
- pushes the new system prompt to Langfuse
- writes the new skill file to disk
- uploads the new eval cases to the Langfuse evaluation dataset

Nodes will be added in a later slice.
"""
