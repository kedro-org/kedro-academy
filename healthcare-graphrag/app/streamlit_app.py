"""Healthcare Knowledge Graph — Streamlit demo app."""
import json
import pickle
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
# OSC 8 hyperlinks: ESC ] 8 ; params ; uri ST  visible-text  ESC ] 8 ;; ST
# ST is either BEL (\x07) or ESC \ (\x1b\). Keep visible text, drop the rest.
_OSC8_LINK = re.compile(
    r"\x1b\]8;[^;]*;[^\x07\x1b]*(?:\x07|\x1b\\)(.*?)\x1b\]8;;(?:\x07|\x1b\\)",
    re.DOTALL,
)
# Any remaining OSC sequences not caught above.
_OSC_STRIP = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")

from ansi2html import Ansi2HTMLConverter
_ANSI_CONV = Ansi2HTMLConverter(inline=True, dark_bg=True)

import streamlit as st

_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

BASE_DIR = Path(__file__).parent.parent
GRAPH_PATH = BASE_DIR / "data/04_feature/knowledge_graph.json"
GRAPH_HTML_PATH = BASE_DIR / "data/08_reporting/knowledge_graph.html"
CHROMA_PATH = str(BASE_DIR / "data/06_models/chroma_db")
ENTITY_SUMMARIES_PATH = BASE_DIR / "data/03_primary/entity_summaries.pkl"
SQLITE_PATH = BASE_DIR / "data/07_model_output/healthcare_stats.db"
RAW_DATA_PATH = BASE_DIR / "data/01_raw/healthcare_dataset.csv"
VIZ_PORT = 4141

st.set_page_config(
    page_title="Healthcare GraphRAG · Powered by Kedro",
    page_icon="K",
    layout="wide",
)

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

st.markdown("""
<style>
html, body, h1, h2, h3, h4, h5, h6,
p, a, li, td, th, label,
div.stMarkdown, div.stText, div.stAlert,
button, input, textarea,
.hero-title, .hero-sub, .hero-badge,
.pillar-title, .pillar-body,
.step-label, .step-title, .step-body,
.cta-title, .cta-sub, .cta-btn,
.compare-header, .compare-tag,
.flow-step, .flow-sub, .flow-col-label {
    font-family: 'Inter', sans-serif !important;
}
.stApp { background-color: #000000; color: #EFEFEF; }
h1, h2, h3 { color: #FFC900; }

/* ── Link buttons (e.g. Open Kedro-Viz) ── */
div[data-testid="stLinkButton"] a {
    color: #000000 !important;
}

/* ── Inline code ── */
code {
    color: #00FFBC !important;
    background-color: #202020 !important;
}

/* ── Buttons ── */
div[data-testid="stButton"] button,
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-primary"] {
    background-color: #FFC900 !important;
    border: 1px solid #FFC900 !important;
    font-weight: 600 !important;
}
div[data-testid="stButton"] button:hover,
button[data-testid="baseButton-secondary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #FFD96B !important;
    border-color: #FFD96B !important;
}
div[data-testid="stButton"] button *,
div[data-testid="stButton"] button,
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-secondary"] *,
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-primary"] * {
    color: #000000 !important;
}

/* ── Chat input submit button ── */
div[data-testid="stChatInputSubmitButton"] button,
div[data-testid="stChatInputSubmitButton"] button svg,
div[data-testid="stChatInputSubmitButton"] button path,
div[data-testid="stChatInputSubmitButton"] button * {
    fill: #000000 !important;
    stroke: #000000 !important;
    color: #000000 !important;
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
    background-color: #202020 !important;
    border-color: #404040 !important;
}
div[data-testid="stExpander"] details {
    background-color: #202020 !important;
}

/* ── Text inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stChatInputContainer textarea {
    background-color: #202020 !important;
    color: #FFFFFF !important;
    border-color: #404040 !important;
}
.stChatMessage { background-color: #161b22; border-radius: 8px; }

/* ── Hero ── */
.hero-wrap { padding: 4rem 0 3rem; }
.hero-title {
    font-size: 3rem;
    font-weight: 800;
    color: #FFFFFF;
    line-height: 1.15;
    margin: 0 0 0.75rem;
}
.hero-title span { color: #FFC900; }
.hero-sub {
    font-size: 1.2rem;
    color: #EFEFEF;
    margin-bottom: 1.75rem;
    max-width: 680px;
    line-height: 1.65;
}
.hero-badge {
    display: inline-block;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.82rem;
    color: #EFEFEF;
    margin-right: 8px;
    margin-bottom: 8px;
}
.scroll-hint {
    text-align: center;
    color: #30363d;
    font-size: 0.9rem;
    margin-top: 3rem;
    letter-spacing: 0.08em;
}

/* ── Cards ── */
.pillar-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.5rem 1.5rem 1.75rem;
    height: 100%;
}
.pillar-icon { font-size: 1.75rem; margin-bottom: 0.75rem; }
.pillar-title {
    font-size: 1rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 0.6rem;
}
.pillar-body { font-size: 0.9rem; color: #EFEFEF; line-height: 1.65; }

/* ── Step headers ── */
.step-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 4rem 0 0.75rem;
}
.step-num {
    background: #FFC900;
    color: #000000;
    border-radius: 50%;
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
}
.step-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #FFC900;
    margin-bottom: 2px;
}
.step-title { font-size: 1.6rem; font-weight: 700; color: #FFFFFF; line-height: 1.2; }
.step-body {
    color: #EFEFEF;
    font-size: 1rem;
    line-height: 1.7;
    max-width: 740px;
    margin-bottom: 1.5rem;
}

/* ── Closing CTA ── */
.cta-banner {
    background: #FFC90020;
    border: 1px solid #FFC900;
    border-radius: 12px;
    padding: 2rem 2rem 2.25rem;
    margin: 4rem 0 2rem;
    text-align: center;
}
.cta-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 0.5rem;
}
.cta-sub {
    font-size: 0.95rem;
    color: #EFEFEF;
    max-width: 560px;
    margin: 0 auto;
    line-height: 1.6;
}
.cta-sub strong { color: #FFC900; }
.cta-actions { margin-top: 1.25rem; }
.cta-btn {
    display: inline-block;
    border-radius: 8px;
    padding: 0.6rem 1.4rem;
    margin: 0 0.4rem;
    font-size: 0.92rem;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
}
.cta-btn-primary { background: #FFC900; color: #000000; }
.cta-btn-primary:hover { background: #FFD96B; }
.cta-btn-secondary { background: transparent; color: #EFEFEF; border: 1px solid #30363d; }
.cta-btn-secondary:hover { color: #FFFFFF; border-color: #EFEFEF; }

/* ── Comparison columns ── */
.compare-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #FFFFFF;
    margin-bottom: 0.4rem;
}
.compare-tag {
    display: inline-block;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
}
.tag-rag { background: #21262d; color: #EFEFEF; border: 1px solid #30363d; }
.tag-graphrag { background: #FFC900; color: #000000; border: 1px solid #FFC900; }

/* ── RAG / GraphRAG flow diagrams ── */
.flow-step {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    font-size: 0.82rem;
    color: #FFFFFF;
    text-align: center;
}
.flow-step.step-primary { background: #FFC900; border-color: #FFC900; color: #000000; }
.flow-step.step-graph   { background: #00FFBC; border-color: #00FFBC; color: #000000; }
.flow-step.step-result  { background: #EFEFEF; border-color: #EFEFEF; color: #000000; }
.flow-step { font-weight: 600; }
.flow-sub { font-size: 0.72rem; font-weight: 400; color: #EFEFEF; display: block; margin-top: 2px; }
.flow-step.step-graph .flow-sub   { color: #000000; }
.flow-step.step-primary .flow-sub { color: #333333; }
.flow-arrow-down { color: #404040; text-align: center; font-size: 1.3rem; line-height: 1.3; }
.flow-col-label {
    font-size: 0.78rem; font-weight: 700; color: #EFEFEF;
    text-align: center; margin-bottom: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Node legend dot ── */
.legend-dot {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
}
</style>
""", unsafe_allow_html=True)


# ── Cache functions ────────────────────────────────────────────────────────────

@st.cache_resource
def start_viz_server() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", VIZ_PORT)) == 0:
            return True
    subprocess.Popen(
        [sys.executable, "-m", "kedro", "viz", "run",
         "--host", "0.0.0.0", "--port", str(VIZ_PORT), "--no-browser"],
        cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(15):
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", VIZ_PORT)) == 0:
                return True
    return False


@st.cache_resource
def load_graph():
    import networkx as nx
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return nx.node_link_graph(json.load(f))


@st.cache_resource
def load_entity_summaries():
    with open(ENTITY_SUMMARIES_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_data
def load_entity_stats():
    import sqlite3
    import pandas as pd
    conn = sqlite3.connect(str(SQLITE_PATH))
    df = pd.read_sql("SELECT * FROM entity_statistics ORDER BY patient_count DESC", conn)
    conn.close()
    return df


@st.cache_data
def load_raw_sample():
    import pandas as pd
    return pd.read_csv(RAW_DATA_PATH, nrows=6)


@st.cache_resource
def load_chroma_collection():
    import chromadb
    return chromadb.PersistentClient(path=CHROMA_PATH).get_collection("healthcare_knowledge")


@st.cache_resource
def load_agent_tools():
    from graphrag.pipelines.query_answering.nodes import build_graph_context_tool, build_search_tool
    graph = load_graph()
    collection = load_chroma_collection()
    search_tool = build_search_tool(knowledge_graph=graph, chroma_collection=collection)
    graph_context_tool = build_graph_context_tool(graph)
    return search_tool, graph_context_tool


@st.cache_resource
def load_openai_client():
    from openai import OpenAI
    from graphrag.utils import get_openai_api_key
    return OpenAI(api_key=get_openai_api_key())


@st.cache_resource
def load_agent_prompt():
    from kedro_datasets_experimental.langchain import PromptDataset
    ds = PromptDataset(
        filepath=str(BASE_DIR / "data/prompts/healthcare_agent.json"),
        template="ChatPromptTemplate",
        dataset={"type": "json.JSONDataset"},
    )
    return ds.load()


# ── Pipeline runner ────────────────────────────────────────────────────────────

def _run_pipelines(pipelines: list[str], label: str):
    import os
    cmd = [sys.executable, "-m", "kedro", "run", "--pipelines", ",".join(pipelines)]
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "FORCE_COLOR": "1"}
    with st.status(label, expanded=True) as status:
        log = st.empty()
        lines: list[str] = []
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=str(BASE_DIR), env=env,
        )
        for line in iter(proc.stdout.readline, ""):
            print(line, end="", flush=True)
            clean = _OSC_STRIP.sub("", _OSC8_LINK.sub(r"\1", line))
            lines.append(clean)
            html_body = _ANSI_CONV.convert("".join(lines), full=False)
            log.html(
                '<div id="kedro-log" style="'
                "height:360px;overflow-y:auto;"
                "background:#0d1117;"
                "font-family:ui-monospace,SFMono-Regular,monospace;"
                "font-size:0.78rem;line-height:1.5;"
                "white-space:pre-wrap;"
                'padding:0.75rem;border-radius:6px;border:1px solid #30363d;">'
                f"{html_body}"
                "<script>"
                "var el=document.getElementById('kedro-log');"
                "if(el)el.scrollTop=el.scrollHeight;"
                "</script>"
                "</div>"
            )
        proc.wait()
        if proc.returncode == 0:
            status.update(label=f"{label} — done ✓", state="complete", expanded=True)
            st.cache_resource.clear()
            st.cache_data.clear()
        else:
            status.update(label=f"{label} — failed ✗", state="error", expanded=True)


# ── Plain RAG (no graph enrichment) ───────────────────────────────────────────

def _plain_rag(question: str) -> dict:
    client = load_openai_client()
    collection = load_chroma_collection()

    embed_response = client.embeddings.create(model="text-embedding-3-small", input=question)
    query_embedding = embed_response.data[0].embedding

    results = collection.query(query_embeddings=[query_embedding], n_results=4)
    docs = results["documents"][0]

    context = "\n\n---\n\n".join(docs)
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": (
                "You are a healthcare data analyst. Answer the user's question "
                "based only on the provided context. Be concise and specific."
            )},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )
    return {"answer": completion.choices[0].message.content, "context_docs": docs}


# ── Load artifacts ─────────────────────────────────────────────────────────────

graph_loaded = False
rag_ready = False

try:
    graph = load_graph()
    entity_summaries = load_entity_summaries()
    graph_loaded = True
except Exception:
    pass

_rag_load_error: Exception | None = None
try:
    openai_client = load_openai_client()
    agent_prompt = load_agent_prompt()
    search_tool, graph_context_tool = load_agent_tools()
    rag_ready = True
except Exception as _e:
    _rag_load_error = _e

viz_available = start_viz_server()


# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<div id="top"></div>', unsafe_allow_html=True)

tab_story, tab_chat, tab_pipeline = st.tabs([
    "The Story",
    "Ask the Graph",
    "Pipeline",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — The Story
# ═══════════════════════════════════════════════════════════════════════════════

with tab_story:

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="hero-wrap">
  <div class="hero-title">Healthcare <span>GraphRAG</span></div>
  <div class="hero-sub">
    55,500 patient records transformed into a queryable knowledge graph —
    see how <strong style="color:#FFFFFF;">Kedro</strong> handles the full pipeline,
    from raw CSV to graph-augmented Q&amp;A, across three storage backends simultaneously.
  </div>
  <div>
    <span class="hero-badge">55,500 synthetic patient records</span>
    <span class="hero-badge">30-node knowledge graph</span>
    <span class="hero-badge">3 storage backends</span>
    <span class="hero-badge">OpenAI GPT-4o</span>
    <span class="hero-badge" style="background:#FFC900;border-color:#FFC900;color:#000000;">◆ Powered by Kedro</span>
    <span class="hero-badge" style="background:#00FFBC;border-color:#00FFBC;color:#000000;">⚠ Synthetic data — no real patients</span>
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">The Problem</div>
  <div class="pillar-body">
    Vector search finds similar text — but medical data is <em>relational</em>.
    Which conditions share treatments? Which insurers see the worst outcomes?
    Flat embeddings lose those connections.
  </div>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">GraphRAG</div>
  <div class="pillar-body">
    A knowledge graph captures entity relationships explicitly.
    At query time the system combines vector search with graph traversal —
    giving the LLM both relevant documents <em>and</em> the relationships that explain them.
  </div>
</div>""", unsafe_allow_html=True)

    with col3:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">Why Kedro</div>
  <div class="pillar-body">
    Kedro handles the entire pipeline — raw CSV → graph → embeddings → Q&amp;A —
    across three storage backends simultaneously. Swap any backend with one line
    in the Data Catalog. No pipeline code changes needed.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown('<div class="scroll-hint">↓ &nbsp; scroll to walk through the pipeline</div>',
                unsafe_allow_html=True)

    # ── Step 1: The Raw Data ───────────────────────────────────────────────────
    st.markdown("""
<div class="step-header">
  <div class="step-num">1</div>
  <div>
    <div class="step-label">Step 1</div>
    <div class="step-title">The Raw Data</div>
  </div>
</div>
<div class="step-body">
  Everything begins with raw data — in this case, 55,500 synthetic patient records from Kaggle,
  each describing a medical condition, prescribed medication, insurance provider, admission type,
  diagnostic test result, and blood type. On its own it is just a table: rows and columns with
  no sense of how any of these things relate to each other.<br><br>
  Kedro's <code>data_ingestion</code> pipeline reads, cleans, and prepares this data — extracting
  the distinct entities (the conditions, medications, insurers, and so on) that will become nodes
  in the knowledge graph.
</div>
""", unsafe_allow_html=True)

    if RAW_DATA_PATH.exists():
        raw_sample = load_raw_sample()
        DISPLAY_COLS = [
            "Name", "Age", "Medical Condition", "Medication",
            "Insurance Provider", "Admission Type", "Test Results", "Blood Type",
        ]
        cols_to_show = [c for c in DISPLAY_COLS if c in raw_sample.columns]
        st.dataframe(raw_sample[cols_to_show] if cols_to_show else raw_sample,
                     width="stretch", height=245)
        st.caption("First 6 rows · `data/01_raw/healthcare_dataset.csv` · 55,500 total records · Synthetic data from Kaggle — no real patient information")
    else:
        st.info("Raw data not found at `data/01_raw/healthcare_dataset.csv`.")

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
    st.markdown(
        "Runs `data_ingestion` + `graph_construction` — cleans the records, "
        "extracts entity summaries, writes statistics to SQLite, and builds the knowledge graph. "
        "Takes ~2 seconds. No API key needed."
    )
    if st.button("▶ Run Graph Pipeline",
                 help="Runs data_ingestion + graph_construction (~2s, no API key needed)"):
        _run_pipelines(["data_ingestion", "graph_construction"], "Running graph pipeline…")

    # ── Step 2: The Knowledge Graph ────────────────────────────────────────────
    st.markdown("""
<div class="step-header">
  <div class="step-num">2</div>
  <div>
    <div class="step-label">Step 2</div>
    <div class="step-title">The Knowledge Graph</div>
  </div>
</div>
""", unsafe_allow_html=True)

    from graphrag.pipelines.graph_construction.nodes import build_d3_graph_html

    col_text, col_example = st.columns([3, 2], gap="large")
    with col_text:
        st.markdown("""
<div class="step-body">
  Instead of storing patient data as rows in a table, a <strong style="color:#FFFFFF;">knowledge
  graph</strong> stores it as a network of connected entities — nodes (the things: conditions,
  medications, insurers) and edges (the relationships between them: <em>TREATED_WITH</em>,
  <em>COVERED_BY</em>, <em>ADMITTED_AS</em>).<br><br>
  The advantage is structural: a table tells you "this patient had Hypertension and took Lipitor."
  A knowledge graph tells you "Hypertension is TREATED_WITH Lipitor — and that relationship appeared
  in 3,200 out of 55,500 patient records." The strength of a connection becomes data.
</div>
""", unsafe_allow_html=True)
    with col_example:
        _mini_graph = {
            "nodes": [
                {"id": "Hypertension", "label": "Hypertension", "color": "#D9506A", "radius": 40,
                 "tooltip": "Condition"},
                {"id": "Lipitor", "label": "Lipitor", "color": "#FFC900", "radius": 24,
                 "tooltip": "Medication"},
                {"id": "Aetna", "label": "Aetna", "color": "#00FFBC", "radius": 24,
                 "tooltip": "Insurer"},
                {"id": "Urgent", "label": "Urgent", "color": "#4A9EF5", "radius": 24,
                 "tooltip": "Admission type"},
                {"id": "Abnormal", "label": "Abnormal", "color": "#F07828", "radius": 24,
                 "tooltip": "Test result"},
            ],
            "links": [
                {"source": "Hypertension", "target": "Lipitor", "width": 2.5, "tooltip": "TREATED_WITH"},
                {"source": "Hypertension", "target": "Aetna", "width": 2.5, "tooltip": "COVERED_BY"},
                {"source": "Hypertension", "target": "Urgent", "width": 2.5, "tooltip": "ADMITTED_AS"},
                {"source": "Hypertension", "target": "Abnormal", "width": 2.5, "tooltip": "SHOWS_RESULT"},
            ],
        }
        st.iframe(build_d3_graph_html(json.dumps(_mini_graph)), height=280)

    st.markdown(
        "<div style='color:#EFEFEF;font-size:0.88rem;margin-top:0.75rem;margin-bottom:1.5rem;'>"
        "The full graph below has <strong style='color:#FFFFFF;'>30 nodes</strong> and "
        "<strong style='color:#FFFFFF;'>120 relationships</strong> derived from all 55,500 records. "
        "Drag to rearrange · scroll to zoom · hover a node to highlight its connections."
        "</div>",
        unsafe_allow_html=True,
    )

    if graph_loaded:
        col_viz, col_meta = st.columns([4, 1])
        with col_meta:
            st.metric("Nodes", graph.number_of_nodes())
            st.metric("Edges", graph.number_of_edges())
            st.markdown("<br>**Node types**", unsafe_allow_html=True)
            for color, label in [
                ("#D9506A", "Medical Condition"),
                ("#FFC900", "Medication"),
                ("#00FFBC", "Insurance Provider"),
                ("#4A9EF5", "Admission Type"),
                ("#F07828", "Test Result"),
                ("#A870DC", "Blood Type"),
            ]:
                st.markdown(
                    f'<span class="legend-dot" style="background:{color};"></span>{label}',
                    unsafe_allow_html=True,
                )
        with col_viz:
            if GRAPH_HTML_PATH.exists():
                st.iframe(GRAPH_HTML_PATH, height=820)
            else:
                st.warning("Graph HTML not found — run **▶ Run Graph Pipeline** above to generate it.")

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown(
            "Runs the `graph_update` pipeline — merges the 5,000 most recent patient records "
            "into the existing graph without rebuilding from scratch. New entities are added; "
            "existing nodes and edges get updated counts. Demonstrates Kedro's incremental update pattern."
        )
        if st.button("▶ Update Graph",
                     help="Merges the 5,000 most recent records into the existing graph"):
            _run_pipelines(["graph_update"], "Merging new patient batch into ontology…")
    else:
        st.info("Run **▶ Run Graph Pipeline** above to build and display the knowledge graph.")

    # ── Step 3: Three Storage Backends ─────────────────────────────────────────
    st.markdown("""
<div class="step-header">
  <div class="step-num">3</div>
  <div>
    <div class="step-label">Step 3</div>
    <div class="step-title">Three Storage Backends</div>
  </div>
</div>
<div class="step-body">
  To query this dataset with GraphRAG, it needs to live in three different stores —
  each serving a different purpose. Kedro populates all three in a single pipeline run,
  and the pipeline code never locks you into specific storage: swap any backend by changing
  one line in the Data Catalog.<br><br>
  Below you can see the relational store live — entity statistics written to SQLite
  by the same pipeline run that built the graph.
</div>
""", unsafe_allow_html=True)

    col_g, col_s, col_v = st.columns(3, gap="medium")
    with col_g:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">Graph Store</div>
  <div class="pillar-body">
    <code>networkx.JSONDataset</code><br><br>
    Persists the full graph with all node and edge attributes as portable JSON.
    Swap the backend via the Kedro Data Catalog —
    no pipeline code changes needed.
  </div>
</div>""", unsafe_allow_html=True)
    with col_s:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">Relational Store</div>
  <div class="pillar-body">
    <code>pandas.SQLTableDataset</code><br><br>
    Writes entity statistics to SQLite — patient counts, billing averages,
    and age distributions per entity. Point the connection string at PostgreSQL
    or BigQuery and the pipeline is unchanged.
  </div>
</div>""", unsafe_allow_html=True)
    with col_v:
        st.markdown("""
<div class="pillar-card">

  <div class="pillar-title">Vector Store</div>
  <div class="pillar-body">
    <code>ChromaDBDataset</code><br><br>
    To search by <em>meaning</em>, each entity document is converted into a vector —
    a list of numbers that encodes what it's about. Similar meanings produce similar
    numbers, so "heart failure" and "cardiac arrest" end up close together.
    ChromaDB stores these vectors and finds the most relevant documents for any question,
    even with no shared keywords.
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    if SQLITE_PATH.exists():
        try:
            entity_stats = load_entity_stats()
            col_filter, col_metric = st.columns([2, 1])
            with col_filter:
                types = ["All"] + sorted(entity_stats["entity_type"].dropna().unique().tolist())
                selected = st.selectbox("Filter by entity type", types)
            with col_metric:
                st.metric("Total entities", len(entity_stats))
            df_show = entity_stats if selected == "All" else entity_stats[entity_stats["entity_type"] == selected]
            st.dataframe(
                df_show.style.format({
                    "avg_billing": "${:,.2f}",
                    "avg_age": "{:.1f}",
                    "avg_stay": "{:.1f}",
                    "patient_count": "{:,}",
                }, na_rep="—"),
                width="stretch",
                height=380,
            )
            st.caption(f"SQLite · `{SQLITE_PATH.relative_to(BASE_DIR)}` · {len(entity_stats)} rows")
        except Exception as e:
            st.error(f"Could not read SQLite store: {e}")

    # ── How it comes together ──────────────────────────────────────────────────
    st.markdown("""
<div class="step-header" style="margin-top:3rem;">
  <div>
    <div class="step-label">Putting it together</div>
    <div class="step-title">From question to answer</div>
  </div>
</div>
<div class="step-body">
  With all three stores populated, the system can answer questions about the data.
  Here is what happens from the moment you type a question — first with plain RAG,
  then with GraphRAG. The only difference is two extra steps, but the quality of the
  answer changes significantly.
</div>
""", unsafe_allow_html=True)

    flow_rag, flow_graphrag = st.columns(2, gap="large")

    _flow_box = (
        lambda text, sub="", cls="":
        f'<div class="flow-step {cls}">{text}'
        + (f'<span class="flow-sub">{sub}</span>' if sub else "")
        + "</div>"
    )
    _arrow = '<div class="flow-arrow-down">↓</div>'

    with flow_rag:
        st.markdown('<div class="flow-col-label">Plain RAG</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;flex-direction:column;gap:0.25rem;">'
            + _flow_box("Your question", cls="step-primary")
            + _arrow
            + _flow_box("Convert to a vector", "text-embedding-3-small finds the meaning<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ pipeline: vector_indexing · embed_documents_node</span>")
            + _arrow
            + _flow_box("Search ChromaDB", "find the 4 most similar entity documents<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: chroma_collection</span>")
            + _arrow
            + _flow_box("Top 4 documents", "raw text, no context about connections<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: rag_documents</span>")
            + _arrow
            + _flow_box("LLM call", sub="pipeline: query_answering · run_agent_node", cls="step-primary")
            + _arrow
            + _flow_box("Answer", cls="step-result")
            + "</div>",
            unsafe_allow_html=True,
        )

    with flow_graphrag:
        st.markdown('<div class="flow-col-label">GraphRAG</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;flex-direction:column;gap:0.25rem;">'
            + _flow_box("Your question", cls="step-primary")
            + _arrow
            + _flow_box("Convert to a vector", "text-embedding-3-small finds the meaning<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ pipeline: vector_indexing · embed_documents_node</span>")
            + _arrow
            + _flow_box("Search ChromaDB", "find the 4 most similar entity documents<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: chroma_collection</span>")
            + _arrow
            + _flow_box("Top 4 documents", "raw text, no context about connections<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: rag_documents</span>")
            + _arrow
            + _flow_box("Graph traversal", "fetch connected entities from the knowledge graph<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: knowledge_graph</span>", "step-graph")
            + _arrow
            + _flow_box("Enriched context", "documents + their relationships<br><span style='font-size:0.65rem;font-family:monospace;opacity:0.75'>↳ catalog: agent_context</span>", "step-graph")
            + _arrow
            + _flow_box("LLM call", sub="pipeline: query_answering · run_agent_node", cls="step-primary")
            + _arrow
            + _flow_box("Answer", cls="step-result")
            + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='color:#EFEFEF;font-size:0.88rem;margin-top:1.25rem;'>"
        "The green steps are what GraphRAG adds. See both approaches answer the same "
        "question live in the <strong style='color:#FFFFFF;'>Ask the Graph</strong> tab."
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown(
        "Runs the full pipeline including `vector_indexing` and `query_answering`. "
        "Embeds all 18 entity documents into ChromaDB using `text-embedding-3-small`. "
        "Requires an OpenAI key in `conf/local/credentials.yml`."
    )
    if st.button("▶ Rebuild Vector Index",
                 help="Runs the full pipeline including embeddings (requires OpenAI key)"):
        _run_pipelines(
            ["data_ingestion", "graph_construction", "vector_indexing", "query_answering"],
            "Running full pipeline…",
        )

    st.html("""
<div class="cta-banner">
  <div class="cta-title">You've seen how it's built — now see what it can do.</div>
  <div class="cta-sub">
    Ask a question about the patient data and watch <strong>GraphRAG</strong> and
    <strong>plain RAG</strong> answer side by side, using the exact graph and vector
    store you just explored.
  </div>
  <div class="cta-actions">
    <a id="cta-ask-graph-btn" class="cta-btn cta-btn-primary" href="javascript:void(0)">Go to Ask the Graph</a>
    <a id="cta-back-top-btn" class="cta-btn cta-btn-secondary" href="javascript:void(0)">↑ Back to top</a>
  </div>
</div>
<script>
  (function() {
    const topBtn = document.getElementById("cta-back-top-btn");
    if (topBtn) {
      topBtn.addEventListener("click", function() {
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
        window.scrollTo(0, 0);
        document.querySelectorAll('section[tabindex], .main, [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"]')
          .forEach(function(el) { el.scrollTop = 0; });
      });
    }
    const btn = document.getElementById("cta-ask-graph-btn");
    if (!btn) return;
    btn.addEventListener("click", function() {
      const tabs = document.querySelectorAll('[data-testid="stTab"]');
      for (const t of tabs) {
        if (t.innerText.includes("Ask the Graph")) {
          t.click();
          setTimeout(function() {
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
            window.scrollTo(0, 0);
            document.querySelectorAll('section[tabindex], .main, [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"]')
              .forEach(function(el) { el.scrollTop = 0; });
          }, 300);
          break;
        }
      }
    });
  })();
</script>
""", unsafe_allow_javascript=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

with tab_pipeline:

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="step-body" style="margin-bottom:2rem;">
  Raw patient records don't become a knowledge graph in one step.
  The pipeline breaks the transformation into four focused stages —
  each with a single responsibility, each producing a named dataset
  that the next stage picks up. Below is the live pipeline map,
  followed by a walkthrough of what each stage does and why.
</div>
""", unsafe_allow_html=True)

    # ── Kedro Viz embed ───────────────────────────────────────────────────────
    if viz_available:
        st.iframe(f"http://localhost:{VIZ_PORT}/?pipeline=graph_construction", height=800)
        st.html(f"""
<script>
(function() {{
  var VIZ_PORT = {VIZ_PORT};
  var TARGET_SRC = 'http://localhost:' + VIZ_PORT + '/?pipeline=graph_construction';

  function findVizFrame() {{
    var frames = document.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {{
      if (frames[i].src && frames[i].src.includes(':' + VIZ_PORT)) {{
        return frames[i];
      }}
    }}
    return null;
  }}

  function reloadViz(f) {{
    f.style.transition = 'opacity 0.2s';
    f.style.opacity = '0';
    setTimeout(function() {{
      f.src = TARGET_SRC + '&_r=2';
      f.addEventListener('load', function onSecondLoad() {{
        f.removeEventListener('load', onSecondLoad);
        f.style.opacity = '1';
      }});
    }}, 200);
  }}

  function waitForStableWidth(f) {{
    var lastWidth = 0;
    var stableCount = 0;
    var interval = setInterval(function() {{
      var w = f.offsetWidth;
      if (w > 0 && w === lastWidth) {{
        stableCount++;
        if (stableCount >= 3) {{
          clearInterval(interval);
          reloadViz(f);
        }}
      }} else {{
        stableCount = 0;
        lastWidth = w;
      }}
    }}, 100);
  }}

  function fixLayout() {{
    var f = findVizFrame();
    if (!f) {{ setTimeout(fixLayout, 300); return; }}
    if (f.dataset.vizFixed) return;
    f.dataset.vizFixed = 'true';
    waitForStableWidth(f);
  }}

  fixLayout();
}})();
</script>
""", unsafe_allow_javascript=True)
    else:
        st.warning("Pipeline visualisation unavailable — make sure `kedro-viz` is installed and re-run the app.")

    # ── Stage cards ───────────────────────────────────────────────────────────
    st.markdown("""
<div class="step-header" style="margin-top:3rem;">
  <div class="step-label">THE FOUR STAGES</div>
</div>
<div class="step-title" style="margin-bottom:2rem;">What each stage does</div>
""", unsafe_allow_html=True)

    stages = [
        {
            "num": "1",
            "name": "data_ingestion",
            "title": "Clean & summarise",
            "body": (
                "Reads the raw CSV, standardises values, and computes per-entity statistics. "
                "Outputs a cleaned DataFrame and entity summaries — the foundation every later stage builds on. "
                "Statistics are written to SQLite so they're queryable without touching the graph."
            ),
            "outputs": ["cleaned_healthcare_data", "entity_summaries", "entity_stats → SQLite"],
        },
        {
            "num": "2",
            "name": "graph_construction",
            "title": "Build the graph",
            "body": (
                "Turns entity summaries into a 30-node NetworkX graph with typed edges "
                "(`TREATED_WITH`, `COVERED_BY`, `ADMITTED_AS`, `SHOWS_RESULT`, `ASSOCIATED_WITH`). "
                "Also renders the interactive D3.js visualisation you saw in The Story tab."
            ),
            "outputs": ["knowledge_graph → JSON", "knowledge_graph.html"],
        },
        {
            "num": "3",
            "name": "vector_indexing",
            "title": "Embed & index",
            "body": (
                "Converts entity summaries into documents that combine text and graph context, "
                "then embeds them with `text-embedding-3-small` and stores the vectors in ChromaDB. "
                "This is what makes semantic search possible in the Ask the Graph tab."
            ),
            "outputs": ["rag_documents", "chroma_collection → ChromaDB"],
        },
        {
            "num": "4",
            "name": "query_answering",
            "title": "Answer questions",
            "body": (
                "Wires together the OpenAI client, the agent prompt, and two retrieval tools "
                "into an `LLMContext` — then runs a function-calling loop that searches ChromaDB "
                "and traverses the graph before generating an answer."
            ),
            "outputs": ["agent_context", "agent_report → JSON"],
        },
    ]

    card_cols = st.columns(4, gap="medium")
    for col, stage in zip(card_cols, stages):
        with col:
            st.markdown(f"""
<div class="pillar-card" style="height:auto;">
  <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.75rem;">
    <div class="step-num" style="width:28px;height:28px;font-size:0.85rem;">{stage["num"]}</div>
    <code style="font-size:0.78rem;">{stage["name"]}</code>
  </div>
  <div class="pillar-title">{stage["title"]}</div>
  <div class="pillar-body" style="margin-bottom:1rem;">{stage["body"]}</div>
  <div style="font-size:0.75rem;font-weight:600;color:#FFC900;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;">Outputs</div>
  {"".join(f'<div style="font-size:0.78rem;color:#EFEFEF;margin-bottom:0.2rem;">· <code>{o}</code></div>' for o in stage["outputs"])}
</div>
""", unsafe_allow_html=True)

    # ── Graph update ──────────────────────────────────────────────────────────
    st.markdown("""
<div class="step-header" style="margin-top:3.5rem;">
  <div class="step-label">KEEPING IT CURRENT</div>
</div>
<div class="step-title" style="margin-bottom:0.75rem;">Updating the graph</div>
<div class="step-body">
  A fifth pipeline — <code>graph_update</code> — handles new data without rebuilding from scratch.
  It reads the 5,000 most recent records, merges them into the existing graph,
  and updates edge counts. New entities are added; existing ones are updated in place.
  It's excluded from the default run to prevent conflicts with <code>graph_construction</code>,
  which writes to the same output file.
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Ask the Graph (GraphRAG vs Plain RAG)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_chat:
    st.markdown("### GraphRAG vs Plain RAG")
    st.markdown(
        "Type a question below. Both systems search the same ChromaDB vector index — "
        "but **GraphRAG** adds related entities from the graph before "
        "calling GPT-4o. The expander under each answer shows exactly what context "
        "the model received."
    )

    col_rag_hdr, col_graph_hdr = st.columns(2, gap="large")
    with col_rag_hdr:
        st.markdown("""
<div class="compare-header">Plain RAG</div>
<span class="compare-tag tag-rag">vector search only</span>
<p style="color:#EFEFEF;font-size:0.9rem;line-height:1.6;">
Embeds the question, fetches the 4 most similar entity documents from ChromaDB,
and passes the raw text directly to GPT-4o. Fast and simple — but the model
sees documents in isolation, with no knowledge of how entities relate to each other.
</p>""", unsafe_allow_html=True)

    with col_graph_hdr:
        st.markdown("""
<div class="compare-header">GraphRAG</div>
<span class="compare-tag tag-graphrag">vector search + graph traversal</span>
<p style="color:#EFEFEF;font-size:0.9rem;line-height:1.6;">
Same ChromaDB search — but each retrieved document is then enriched with
connected entities from the knowledge graph. The model receives the semantic results
<em>and</em> the structural relationships between them, enabling more connected answers.
</p>""", unsafe_allow_html=True)

    st.divider()

    if not rag_ready:
        if _rag_load_error is not None:
            st.error(f"Failed to load Q&A components: {_rag_load_error}")
            st.exception(_rag_load_error)
        else:
            st.warning(
                "Run **Rebuild Vector Index** in The Story tab to enable Q&A. "
                "The graph visualization works without it."
            )
    else:
        SAMPLE_QUESTIONS = [
            "Which medical conditions have the highest billing costs?",
            "What medications are most commonly prescribed for cancer?",
            "Which insurance provider covers the most emergency admissions?",
            "How do test results vary across different conditions?",
        ]

        st.markdown(
            "<div style='color:#EFEFEF;font-size:0.85rem;margin-bottom:0.5rem;'>"
            "Try: " + " · ".join(f"<em>{q}</em>" for q in SAMPLE_QUESTIONS)
            + "</div>",
            unsafe_allow_html=True,
        )

        question = st.chat_input("Ask a question to compare both approaches…")

        if "comparison" not in st.session_state:
            st.session_state.comparison = None

        if question:
            from graphrag.pipelines.query_answering.nodes import _run_agent

            col_rag, col_graph = st.columns(2, gap="large")

            with col_rag:
                with st.spinner("Plain RAG searching…"):
                    rag_result = _plain_rag(question)

            with col_graph:
                with st.spinner("GraphRAG searching…"):
                    graphrag_result = _run_agent(
                        question=question,
                        prompt_template=agent_prompt,
                        openai_client=openai_client,
                        search_tool=search_tool,
                        graph_context_tool=graph_context_tool,
                    )

            st.session_state.comparison = {
                "question": question,
                "rag": rag_result,
                "graphrag": graphrag_result,
            }

        if st.session_state.comparison:
            comp = st.session_state.comparison
            st.markdown(
                f"<div style='color:#00FFBC;font-weight:600;margin-bottom:1rem;'>"
                f"Q: {comp['question']}</div>",
                unsafe_allow_html=True,
            )

            col_rag, col_graph = st.columns(2, gap="large")

            with col_rag:
                st.markdown(comp["rag"]["answer"])
                with st.expander("Context the model received"):
                    for i, doc in enumerate(comp["rag"]["context_docs"], 1):
                        st.markdown(f"**Document {i}**")
                        st.text(doc)

            with col_graph:
                st.markdown(comp["graphrag"]["answer"])
                if comp["graphrag"]["tool_calls"]:
                    with st.expander(
                        f"Context + graph enrichment · "
                        f"{len(comp['graphrag']['tool_calls'])} tool call(s)"
                    ):
                        for tc in comp["graphrag"]["tool_calls"]:
                            st.markdown(f"**`{tc['tool']}`** — `{tc['args']}`")
                            st.text(tc["result"])
