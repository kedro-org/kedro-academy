"""Nodes for the ``reflection`` pipeline.

The meta-agent reads traces + scores + the current prompt + the current skill
file, then proposes:
- a narrative summary (what failed, what is being changed, why)
- a new system prompt
- an updated skill file
- new eval cases derived from failures

Nodes will be added in a later slice.
"""
