"""Streamlit dashboard entry point for the B2B campaign agent reflection demo.

Run with:  streamlit run app/main.py
"""

import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="B2B Campaign Agent — Reflection Demo",
        layout="wide",
    )
    st.title("B2B Campaign Agent — Reflection Demo")
    st.caption("Scaffold only — steps and components will be wired up in later slices.")


if __name__ == "__main__":
    main()
