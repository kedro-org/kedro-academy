"""Global CSS for the Reflection Hub Streamlit app.

Inject once at the top of each page via:
    from app.styles import inject_css
    inject_css()
"""

from __future__ import annotations

import streamlit as st

GLOBAL_CSS = """
<style>
  /* ── Typography — Inter from link tag above ── */
  html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    font-size: 14px !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
    /* No color here — it cascades into button internals via Base Web's color:inherit chain
       and overrides the white text on primary buttons even with !important on the button. */
  }
  [class*="css"],
  [data-testid="stAppViewContainer"],
  [data-testid="stMarkdownContainer"],
  [data-testid="stText"],
  button, input, select, textarea {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    -moz-osx-font-smoothing: grayscale !important;
  }
  /* Markdown paragraphs match HTML body text */
  [data-testid="stMarkdownContainer"] p {
    font-size: 13.5px !important;
    line-height: 1.6 !important;
    color: #0F172A !important;
  }

  /* ── App background ── */
  [data-testid="stAppViewContainer"] {
    background: #F8FAFC !important;
  }
  [data-testid="stAppViewContainer"] > .main {
    background: #F8FAFC !important;
    padding-top: 0 !important;
  }
  .block-container {
    max-width: 1280px !important;
    padding-top: 1rem !important;
    padding-bottom: 4rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
  }

  /* ── Hide Streamlit chrome ── */
  header[data-testid="stHeader"] { display: none !important; }
  [data-testid="stToolbar"] { display: none !important; }
  #MainMenu { display: none !important; }
  footer { display: none !important; }
  [data-testid="collapsedControl"] { display: none !important; }
  [data-testid="stDecoration"] { display: none !important; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] { display: none !important; }

  /* ── Cards — match mockup exactly ── */
  .card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    padding: 20px 24px;
    margin-bottom: 12px;
  }
  .card-sm {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    padding: 14px 18px;
    margin-bottom: 10px;
  }
  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  .card-title {
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.01em;
  }

  /* ── Reset Demo button — fixed into the nav bar's right side ─────────────
     #rh-nav-reset is a hidden anchor at the end of the nav st.markdown call.
     The st.button rendered immediately after creates the adjacent sibling
     element-container which CSS positions fixed at the top-right of the page.
  ── */
  .element-container:has(#rh-nav-reset) + .element-container {
    position: fixed !important;
    top: 11px !important;
    right: 24px !important;
    z-index: 999999 !important;
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  .element-container:has(#rh-nav-reset) + .element-container [data-testid="stBaseButton-secondary"],
  .element-container:has(#rh-nav-reset) + .element-container .stButton button {
    font-size: 12.5px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    padding: 5px 12px !important;
    box-shadow: none !important;
  }
  .element-container:has(#rh-nav-reset) + .element-container [data-testid="stBaseButton-secondary"]:hover,
  .element-container:has(#rh-nav-reset) + .element-container .stButton button:hover {
    background: #E2E8F0 !important;
    color: #0F172A !important;
  }
  .element-container:has(#rh-nav-reset) + .element-container [data-testid="stBaseButton-secondary"] *,
  .element-container:has(#rh-nav-reset) + .element-container .stButton button * {
    color: inherit !important;
  }

  /* ── Nav ── */
  .nav-bar {
    display: flex;
    align-items: center;
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 0 24px;
    height: 56px;
    position: sticky;
    top: 0;
    z-index: 1000;
    gap: 32px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .nav-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #0F172A;
    text-decoration: none;
    letter-spacing: -0.02em;
    margin-right: 16px;
  }
  .nav-logo-icon {
    width: 28px;
    height: 28px;
    background: #2251FF;
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 14px;
  }
  .nav-links {
    display: flex;
    align-items: center;
    gap: 4px;
    flex: 1;
  }
  .nav-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: #64748B;
    text-decoration: none;
    transition: all 0.15s;
    cursor: pointer;
    border: none;
    background: transparent;
  }
  .nav-link:hover {
    background: #F1F5F9;
    color: #0F172A;
  }
  .nav-link.active {
    background: #EEF2FF;
    color: #2251FF;
    font-weight: 600;
  }

  /* ── Pills / badges ── */
  .pill {
    display: inline-flex;
    align-items: center;
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.01em;
  }
  .pill-blue { background: #EEF2FF; color: #2251FF; }
  .pill-green { background: #DCFCE7; color: #15803D; }
  .pill-amber { background: #FEF9C3; color: #92400E; }
  .pill-red { background: #FEE2E2; color: #B91C1C; }
  .pill-slate { background: #F1F5F9; color: #64748B; }
  .pill-purple { background: #F3E8FF; color: #7C3AED; }

  /* ══════════════════════════════════════════════════════════
     Agent selector — st.pills pill bar container
  ══════════════════════════════════════════════════════════ */
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-pills"]),
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-pillsActive"]) {
    background: #F1F5F9 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 2px !important;
    border: none !important;
    margin-bottom: 8px !important;
  }
  /* Inactive pill */
  [data-testid="stBaseButton-pills"] {
    border-radius: 10px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    background: transparent !important;
    border: 1.5px solid transparent !important;
    padding: 7px 16px !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.15s !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  [data-testid="stBaseButton-pills"]:hover {
    background: rgba(255,255,255,0.7) !important;
    color: #1E293B !important;
  }
  /* Active pill — blue border, white bg */
  [data-testid="stBaseButton-pillsActive"] {
    border-radius: 10px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    color: #2251FF !important;
    background: #FFFFFF !important;
    border: 1.5px solid #2251FF !important;
    padding: 7px 16px !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.10) !important;
    display: inline-flex !important;
    align-items: center !important;
  }
  /* Hide widget label */
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-pills"]) label,
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-pillsActive"]) label {
    display: none !important;
  }

  /* ── SVG icon squares via ::before — matches header card icons exactly ────
     Scoped to pills-style ButtonGroup only.
     Targets buttons by nth-of-type inside [data-baseweb="button-group"].
  ── */
  [data-testid="stButtonGroup"]:has([data-testid^="stBaseButton-pills"])
    [data-baseweb="button-group"] button::before {
    content: "" !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 20px !important;
    height: 20px !important;
    min-width: 20px !important;
    border-radius: 5px !important;
    margin-right: 7px !important;
    background-size: 13px 13px !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
  }
  /* B2B Sales — briefcase, #2251FF on #EEF2FF */
  [data-testid="stButtonGroup"]:has([data-testid^="stBaseButton-pills"])
    [data-baseweb="button-group"] button:nth-of-type(1)::before {
    background-color: #EEF2FF !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='%232251FF' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='2' y='7' width='20' height='14' rx='2' ry='2'/%3E%3Cpath d='M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16'/%3E%3C/svg%3E") !important;
  }
  /* Consumer Marketing — bar-chart-2, #8B5CF6 on #F5F3FF */
  [data-testid="stButtonGroup"]:has([data-testid^="stBaseButton-pills"])
    [data-baseweb="button-group"] button:nth-of-type(2)::before {
    background-color: #F5F3FF !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='%238B5CF6' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='18' y1='20' x2='18' y2='10'/%3E%3Cline x1='12' y1='20' x2='12' y2='4'/%3E%3Cline x1='6' y1='20' x2='6' y2='14'/%3E%3Cline x1='2' y1='20' x2='22' y2='20'/%3E%3C/svg%3E") !important;
  }
  /* Customer Care — headphones, #00C4B4 on #F0FDFA */
  [data-testid="stButtonGroup"]:has([data-testid^="stBaseButton-pills"])
    [data-baseweb="button-group"] button:nth-of-type(3)::before {
    background-color: #F0FDFA !important;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='13' viewBox='0 0 24 24' fill='none' stroke='%2300C4B4' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 18v-6a9 9 0 0 1 18 0v6'/%3E%3Cpath d='M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z'/%3E%3C/svg%3E") !important;
  }

  /* ══════════════════════════════════════════════════════════
     st.segmented_control — pipeline picker & log filters
     Compact style matching the HTML .log-filter-btn / .viz-pip-btn
  ══════════════════════════════════════════════════════════ */
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-segmented_control"]),
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-segmented_controlActive"]) {
    background: #F1F5F9 !important;
    border-radius: 8px !important;
    padding: 3px !important;
    gap: 0 !important;
    border: none !important;
    display: inline-flex !important;
  }
  [data-testid="stBaseButton-segmented_control"] {
    border-radius: 6px !important;
    font-size: 11.5px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    background: transparent !important;
    border: none !important;
    padding: 4px 10px !important;
    font-family: 'Inter', sans-serif !important;
    transition: all 0.15s !important;
  }
  [data-testid="stBaseButton-segmented_control"]:hover {
    color: #1E293B !important;
  }
  [data-testid="stBaseButton-segmented_controlActive"] {
    border-radius: 6px !important;
    font-size: 11.5px !important;
    font-weight: 600 !important;
    color: #1E293B !important;
    background: #FFFFFF !important;
    border: none !important;
    padding: 4px 10px !important;
    font-family: 'Inter', sans-serif !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.10) !important;
  }
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-segmented_control"]) label,
  [data-testid="stButtonGroup"]:has([data-testid="stBaseButton-segmented_controlActive"]) label {
    display: none !important;
  }

  /* ── Agent tabs (fallback custom HTML) ── */
  .agent-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .agent-tab {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    color: #64748B;
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    cursor: pointer;
    transition: all 0.15s;
  }
  .agent-tab:hover {
    background: #F8FAFC;
    border-color: #CBD5E1;
  }
  .agent-tab.active {
    background: #EEF2FF;
    border-color: #2251FF;
    color: #2251FF;
    font-weight: 600;
  }

  /* ── Stage tabs ── */
  .stage-tabs {
    display: flex;
    gap: 4px;
    padding: 4px;
    background: #F1F5F9;
    border-radius: 10px;
    margin-bottom: 20px;
  }
  .stage-tab {
    flex: 1;
    text-align: center;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .stage-tab:hover {
    background: rgba(255,255,255,0.6);
    color: #0F172A;
  }
  .stage-tab.active {
    background: #FFFFFF;
    color: #2251FF;
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }

  /* ── Sub-tabs ── */
  .sub-tab {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #64748B;
    background: transparent;
    border: none;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.12s;
  }
  .sub-tab:hover { color: #0F172A; }
  .sub-tab.active {
    color: #2251FF;
    border-bottom-color: #2251FF;
    font-weight: 600;
  }

  /* ── Score bars ── */
  .score-bar-wrap {
    margin-bottom: 10px;
  }
  .score-bar-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #0F172A;
    margin-bottom: 4px;
    font-weight: 500;
  }
  .score-bar-track {
    height: 8px;
    background: #F1F5F9;
    border-radius: 100px;
    overflow: hidden;
  }
  .score-bar-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 0.4s ease;
  }
  .score-bar-fill.green { background: #22C55E; }
  .score-bar-fill.amber { background: #F59E0B; }
  .score-bar-fill.red { background: #EF4444; }

  /* ── Log terminal ── */
  .log-terminal {
    background: #0F172A;
    border-radius: 10px;
    padding: 16px;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.6;
    color: #94A3B8;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
  .log-line-info { color: #94A3B8; }
  .log-line-error { color: #F87171; }
  .log-line-success { color: #4ADE80; }
  .log-line-warning { color: #FBBF24; }

  /* ── Command strip ── */
  .command-strip {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #0F172A;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .command-text {
    font-family: 'Menlo', 'Monaco', monospace;
    font-size: 13px;
    color: #7DD3FC;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .command-pill {
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    background: rgba(255,255,255,0.08);
    color: #CBD5E1;
    white-space: nowrap;
  }

  /* ── KPI / metric cards ── */
  .kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
  }
  .kpi-label {
    font-size: 11px;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
  }
  .kpi-value {
    font-size: 26px;
    font-weight: 800;
    color: #0F172A;
    line-height: 1;
    letter-spacing: -0.02em;
  }
  .kpi-delta {
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
  }
  .kpi-delta.positive { color: #15803D; }
  .kpi-delta.negative { color: #B91C1C; }

  /* ── Signals table ── */
  .signals-table {
    width: 100%;
    border-collapse: collapse;
  }
  .signals-table th {
    font-size: 11px;
    font-weight: 700;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #E2E8F0;
  }
  .signals-table td {
    font-size: 13px;
    color: #0F172A;
    padding: 10px 12px;
    border-bottom: 1px solid #F1F5F9;
    vertical-align: top;
  }
  .signals-table tr:last-child td { border-bottom: none; }

  /* ── Approval gate ── */
  .approval-gate {
    background: #FFFBEB;
    border: 1px solid #F59E0B;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .approval-gate-title {
    font-size: 16px;
    font-weight: 700;
    color: #92400E;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* ── Diff panels ── */
  .diff-panel {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 16px;
    font-family: 'Menlo', 'Monaco', monospace;
    font-size: 12.5px;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    border: 1px solid #E2E8F0;
    max-height: 320px;
    overflow-y: auto;
  }
  .diff-panel.before { border-top: 3px solid #F87171; }
  .diff-panel.after { border-top: 3px solid #4ADE80; }

  /* ══════════════════════════════════════════════════════════
     ALL st.tabs: common tab-bar styles
  ══════════════════════════════════════════════════════════ */
  [data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0 !important;
    border-bottom: 1px solid #E2E8F0 !important;
    background: transparent !important;
    padding: 0 8px !important;
  }
  [data-testid="stTabs"] [data-baseweb="tab"] {
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: #64748B !important;
    padding: 10px 18px !important;
    border-bottom: 3px solid transparent !important;
    background: transparent !important;
    font-family: 'Inter', sans-serif !important;
    white-space: nowrap !important;
  }
  [data-testid="stTabs"] [data-baseweb="tab"] p {
    margin: 0 !important;
  }
  [data-testid="stTabs"] [aria-selected="true"] {
    color: #2251FF !important;
    border-bottom: 3px solid #2251FF !important;
    font-weight: 600 !important;
  }
  [data-baseweb="tab-highlight"] { background-color: #2251FF !important; height: 3px !important; }
  [data-baseweb="tab-border"] { background-color: #E2E8F0 !important; }
  [data-testid="stTabs"] [data-baseweb="tab-panel"] { padding: 4px 0 16px 0 !important; }

  /* ══════════════════════════════════════════════════════════
     Stage tabs: NO extra card border here — the card comes
     from st.container(border=True) in pages/campaign.py.
     The [data-testid="stTabs"] inside the container gets no
     extra border, just transparent background.
  ══════════════════════════════════════════════════════════ */
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin: 0 !important;
  }

  /* ══════════════════════════════════════════════════════════
     Numbered circle badges on STAGE tabs (1 2 3 4)
     Use :not([data-baseweb="tab-panel"] *) to exclude sub-tabs.
  ══════════════════════════════════════════════════════════ */

  /* Stage tab p labels: flex with gap */
  [data-testid="stVerticalBlockBorderWrapper"]
    [data-testid="stTabs"] [data-baseweb="tab"] p {
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin: 0 !important;
  }

  /* Number circles via ::before — use button:nth-of-type so non-tab Base Web
     siblings (highlight bar, border line) don't offset the count */
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button:nth-of-type(1) p::before { content: "1"; }
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button:nth-of-type(2) p::before { content: "2"; }
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button:nth-of-type(3) p::before { content: "3"; }
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button:nth-of-type(4) p::before { content: "4"; }

  /* Circle style: grey (inactive) */
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button p::before {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    width: 18px !important;
    height: 18px !important;
    min-width: 18px !important;
    border-radius: 50% !important;
    background: #E2E8F0 !important;
    color: #64748B !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    line-height: 18px !important;
  }
  /* Active: blue circle */
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTabs"]
    [data-baseweb="tab-list"] button[aria-selected="true"] p::before {
    background: #2251FF !important;
    color: #FFFFFF !important;
  }

  /* Suppress number badges on nested (sub) tabs */
  [data-baseweb="tab-panel"] [data-baseweb="tab"] p::before {
    display: none !important;
  }
  /* Sub-tabs: slightly smaller text */
  [data-baseweb="tab-panel"] [data-testid="stTabs"] [data-baseweb="tab"] {
    font-size: 12.5px !important;
    padding: 7px 14px !important;
  }

  /* ── st.container(border=True) → card appearance matching other cards ── */
  [data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    padding: 20px 24px !important;
    margin-bottom: 12px !important;
  }
  /* Remove double-border: the inner stVerticalBlock already has bg */
  [data-testid="stVerticalBlockBorderWrapper"] > div {
    border: none !important;
    padding: 0 !important;
  }

  /* ── Tighten vertical spacing ── */
  .element-container { margin-bottom: 0.35rem !important; }
  [data-testid="stHorizontalBlock"] { gap: 8px !important; align-items: center; }

  /* ── Allow SVG inline in markdown ── */
  [data-testid="stMarkdownContainer"] svg {
    display: inline-block !important;
    vertical-align: middle !important;
    overflow: visible !important;
  }

  /* ── Buttons (Streamlit 1.36+ uses stBaseButton-{kind}) ── */
  /* Primary button — three selectors for full coverage.
     .stButton is the class Streamlit always puts on the outer wrapper div.
     Descendant * rule catches Base Web's inner label span/div which uses color:inherit. */
  [data-testid="stBaseButton-primary"],
  .stButton button[kind="primary"],
  .stButton button {
    background: #2251FF !important;
    border-color: #2251FF !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 0.45rem 1.25rem !important;
    font-size: 13px !important;
    font-family: 'Inter', sans-serif !important;
  }
  [data-testid="stBaseButton-primary"] *,
  .stButton button * {
    color: #FFFFFF !important;
  }
  [data-testid="stBaseButton-primary"]:hover,
  .stButton button:hover {
    background: #1A3FCC !important;
    border-color: #1A3FCC !important;
  }
  [data-testid="stBaseButton-secondary"] {
    border: 1.5px solid #E2E8F0 !important;
    color: #0F172A !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 7px 14px !important;
    background: #FFFFFF !important;
    font-family: 'Inter', sans-serif !important;
  }
  [data-testid="stBaseButton-secondary"]:hover {
    background: #F8FAFC !important;
    border-color: #CBD5E1 !important;
    color: #0F172A !important;
  }

  /* ── Metrics ── */
  [data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 14px 18px;
  }
  [data-testid="stMetricLabel"] {
    font-size: 11px !important;
    color: #94A3B8 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600 !important;
  }
  [data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 800 !important;
    color: #0F172A !important;
    letter-spacing: -0.02em !important;
  }
  [data-testid="stMetricDelta"] {
    font-size: 13px !important;
    font-weight: 600 !important;
  }

  /* ── Alerts ── */
  [data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 14px !important;
  }

  /* ── Code blocks ── */
  div[data-testid="stCode"] pre {
    background: #0F172A !important;
    color: #94A3B8 !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
    border-radius: 10px !important;
    padding: 16px !important;
    white-space: pre-wrap !important;
  }

  /* ── Columns gap fix ── */
  [data-testid="column"] { padding: 0 8px !important; }
  [data-testid="stHorizontalBlock"] { gap: 0; }

  /* ── Divider ── */
  hr {
    border: none !important;
    border-top: 1px solid #E2E8F0 !important;
    margin: 1.5rem 0 !important;
  }

  /* ── Expander ── */
  [data-testid="stExpander"] {
    border: 1px solid #E2E8F0 !important;
    border-radius: 10px !important;
    background: #FFFFFF !important;
  }
  [data-testid="stExpander"] summary {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #0F172A !important;
  }

  /* ── Select / radio ── */
  [data-testid="stRadio"] label {
    font-size: 14px !important;
    color: #0F172A !important;
  }
</style>
"""


def inject_css() -> None:
    """Inject Inter font (via link tag) then the global CSS."""
    # Link tag is more reliable than @import inside <style>
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;'
        '0,500;0,600;0,700;0,800&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
