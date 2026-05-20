"""Subprocess wrapper around `kedro run`.

The Streamlit dashboard invokes Kedro pipelines through this module so the UI
never imports Kedro directly. Pipelines write their artifacts to ``data/`` and
the dashboard reads them back from disk and from Langfuse.
"""
