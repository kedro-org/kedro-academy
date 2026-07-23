"""Graph construction pipeline nodes."""
import copy
import logging
from pathlib import Path

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)


def _node_tooltip(label: str, node_type: str, count: int) -> str:
    return f"<b>{label}</b><br>Type: {node_type}<br>Patients: {count:,}"


def build_knowledge_graph(df: pd.DataFrame, node_colors: dict) -> nx.Graph:
    G = nx.Graph()

    for cond in df["Medical Condition"].unique():
        n = len(df[df["Medical Condition"] == cond])
        G.add_node(cond, node_type="condition", color=node_colors["condition"], count=n,
                   title=_node_tooltip(cond, "Medical Condition", n))

    for med in df["Medication"].unique():
        n = len(df[df["Medication"] == med])
        G.add_node(med, node_type="medication", color=node_colors["medication"], count=n,
                   title=_node_tooltip(med, "Medication", n))

    for ins in df["Insurance Provider"].unique():
        n = len(df[df["Insurance Provider"] == ins])
        G.add_node(ins, node_type="insurer", color=node_colors["insurer"], count=n,
                   title=_node_tooltip(ins, "Insurance Provider", n))

    for adm in df["Admission Type"].unique():
        n = len(df[df["Admission Type"] == adm])
        G.add_node(adm, node_type="admission_type", color=node_colors["admission_type"], count=n,
                   title=_node_tooltip(adm, "Admission Type", n))

    for res in df["Test Results"].unique():
        n = len(df[df["Test Results"] == res])
        G.add_node(res, node_type="test_result", color=node_colors["test_result"], count=n,
                   title=_node_tooltip(res, "Test Result", n))

    for bt in df["Blood Type"].unique():
        n = len(df[df["Blood Type"] == bt])
        G.add_node(bt, node_type="blood_type", color=node_colors["blood_type"], count=n,
                   title=_node_tooltip(bt, "Blood Type", n))

    for (cond, med), n in df.groupby(["Medical Condition", "Medication"]).size().items():
        G.add_edge(cond, med, weight=int(n), relationship="TREATED_WITH",
                   title=f"TREATED_WITH<br>{n:,} patients")

    for (cond, ins), n in df.groupby(["Medical Condition", "Insurance Provider"]).size().items():
        G.add_edge(cond, ins, weight=int(n), relationship="COVERED_BY",
                   title=f"COVERED_BY<br>{n:,} patients")

    for (cond, adm), n in df.groupby(["Medical Condition", "Admission Type"]).size().items():
        G.add_edge(cond, adm, weight=int(n), relationship="ADMITTED_AS",
                   title=f"ADMITTED_AS<br>{n:,} cases")

    for (cond, res), n in df.groupby(["Medical Condition", "Test Results"]).size().items():
        G.add_edge(cond, res, weight=int(n), relationship="SHOWS_RESULT",
                   title=f"SHOWS_RESULT<br>{n:,} cases")

    # Top-2 blood types per condition to add richness without clutter
    for cond in df["Medical Condition"].unique():
        top_bt = df[df["Medical Condition"] == cond]["Blood Type"].value_counts().head(4)
        for bt, n in top_bt.items():
            G.add_edge(cond, bt, weight=int(n), relationship="ASSOCIATED_WITH",
                       title=f"ASSOCIATED_WITH<br>{n:,} patients")

    logger.info("Knowledge graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())
    return G


def update_knowledge_graph(
    existing_graph: nx.Graph,
    df: pd.DataFrame,
    node_colors: dict,
    update_batch_size: int,
) -> nx.Graph:
    """Merge a batch of new records into an existing knowledge graph.

    Simulates new data arriving after the initial ontology was built.
    Uses create-or-update semantics: existing nodes/edges get updated counts,
    new entities are added. Storage backend is swappable via the Kedro catalog
    Storage backend is swappable via the Kedro catalog with no changes to this node.
    """
    G = copy.deepcopy(existing_graph)

    new_records = df.sort_values("Date of Admission").tail(update_batch_size)
    logger.info(
        "Merging %d new records into existing graph (%d nodes, %d edges)",
        len(new_records), G.number_of_nodes(), G.number_of_edges(),
    )

    new_nodes = updated_nodes = new_edges = updated_edges = 0

    entity_cols = [
        ("Medical Condition", "condition",     "Medical Condition", node_colors["condition"]),
        ("Medication",        "medication",    "Medication",        node_colors["medication"]),
        ("Insurance Provider","insurer",       "Insurance Provider",node_colors["insurer"]),
        ("Admission Type",    "admission_type","Admission Type",    node_colors["admission_type"]),
        ("Test Results",      "test_result",   "Test Result",       node_colors["test_result"]),
        ("Blood Type",        "blood_type",    "Blood Type",        node_colors["blood_type"]),
    ]

    for col, node_type, type_label, color in entity_cols:
        for entity in new_records[col].unique():
            n = int((new_records[col] == entity).sum())
            if G.has_node(entity):
                new_count = G.nodes[entity].get("count", 0) + n
                G.nodes[entity]["count"] = new_count
                G.nodes[entity]["title"] = _node_tooltip(entity, type_label, new_count)
                updated_nodes += 1
            else:
                G.add_node(entity, node_type=node_type, color=color, count=n,
                           title=_node_tooltip(entity, type_label, n))
                new_nodes += 1

    edge_defs = [
        ("Medical Condition", "Medication",        "TREATED_WITH"),
        ("Medical Condition", "Insurance Provider", "COVERED_BY"),
        ("Medical Condition", "Admission Type",    "ADMITTED_AS"),
        ("Medical Condition", "Test Results",      "SHOWS_RESULT"),
    ]

    for col_a, col_b, rel in edge_defs:
        for (a, b), n in new_records.groupby([col_a, col_b]).size().items():
            n = int(n)
            if G.has_edge(a, b):
                new_w = G[a][b].get("weight", 0) + n
                G[a][b]["weight"] = new_w
                G[a][b]["title"] = f"{rel}<br>{new_w:,} patients"
                updated_edges += 1
            else:
                G.add_edge(a, b, weight=n, relationship=rel, title=f"{rel}<br>{n:,} patients")
                new_edges += 1

    for cond in new_records["Medical Condition"].unique():
        top_bt = new_records[new_records["Medical Condition"] == cond]["Blood Type"].value_counts().head(4)
        for bt, n in top_bt.items():
            n = int(n)
            if G.has_edge(cond, bt):
                new_w = G[cond][bt].get("weight", 0) + n
                G[cond][bt]["weight"] = new_w
                G[cond][bt]["title"] = f"ASSOCIATED_WITH<br>{new_w:,} patients"
                updated_edges += 1
            else:
                G.add_edge(cond, bt, weight=n, relationship="ASSOCIATED_WITH",
                           title=f"ASSOCIATED_WITH<br>{n:,} patients")
                new_edges += 1

    logger.info(
        "Merge complete: %d nodes (%d new, %d updated), %d edges (%d new, %d updated)",
        G.number_of_nodes(), new_nodes, updated_nodes,
        G.number_of_edges(), new_edges, updated_edges,
    )
    return G


def build_d3_graph_html(graph_json: str) -> str:
    """Render the standalone D3.js force-graph HTML for a given nodes/links JSON payload.

    Shared by the full knowledge-graph reporting output and any smaller
    illustrative previews that want the same drag/zoom/hover behaviour.
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #000000; overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  svg {{ width: 100vw; height: 100vh; display: block; }}
  .node circle {{ cursor: pointer; transition: filter 0.2s; }}
  .node circle:hover {{ filter: brightness(1.4); }}
  .node text {{
    fill: #ffffff;
    font-size: 11px;
    font-weight: 600;
    pointer-events: none;
    text-anchor: middle;
    dominant-baseline: central;
    text-shadow: 0 0 4px #000;
  }}
  .link {{ fill: none; stroke-opacity: 0.45; transition: stroke-opacity 0.2s; }}
  .link:hover {{ stroke-opacity: 0.9; }}
  #tooltip {{
    position: fixed;
    background: rgba(0,0,0,0.92);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 8px;
    color: #EFEFEF;
    font-size: 12px;
    line-height: 1.6;
    max-width: 220px;
    padding: 8px 12px;
    pointer-events: none;
    white-space: pre-line;
    display: none;
    z-index: 10;
    box-shadow: 0 4px 20px rgba(0,0,0,0.6);
  }}
</style>
</head>
<body>
<svg id="graph"></svg>
<div id="tooltip"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const graphData = {graph_json};

const W = window.innerWidth, H = window.innerHeight;
const svg = d3.select("#graph");
const defs = svg.append("defs");

// glow filter
const filter = defs.append("filter").attr("id", "glow").attr("x", "-50%").attr("y", "-50%").attr("width", "200%").attr("height", "200%");
filter.append("feGaussianBlur").attr("stdDeviation", "3.5").attr("result", "coloredBlur");
const feMerge = filter.append("feMerge");
feMerge.append("feMergeNode").attr("in", "coloredBlur");
feMerge.append("feMergeNode").attr("in", "SourceGraphic");

// arrow marker (unused but keeps edge direction concept)
const g = svg.append("g");

// zoom
const zoomBehavior = d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform));
svg.call(zoomBehavior);

function fitToView() {{
  const xs = graphData.nodes.map(d => d.radius || 20);
  const minX = Math.min(...graphData.nodes.map((d, i) => d.x - xs[i]));
  const maxX = Math.max(...graphData.nodes.map((d, i) => d.x + xs[i]));
  const minY = Math.min(...graphData.nodes.map((d, i) => d.y - xs[i]));
  const maxY = Math.max(...graphData.nodes.map((d, i) => d.y + xs[i]));
  const w = Math.max(maxX - minX, 1), h = Math.max(maxY - minY, 1);
  const scale = Math.min(W / w, H / h, 2) * 0.85;
  const tx = W / 2 - scale * (minX + maxX) / 2;
  const ty = H / 2 - scale * (minY + maxY) / 2;
  svg.transition().duration(400)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}}

const tooltip = document.getElementById("tooltip");

// build maps
const nodeById = new Map(graphData.nodes.map(n => [n.id, n]));

const simulation = d3.forceSimulation(graphData.nodes)
  .force("link", d3.forceLink(graphData.links)
    .id(d => d.id)
    .distance(d => 120 + (1 - d.width / 6) * 80)
    .strength(0.6))
  .force("charge", d3.forceManyBody().strength(-600).distanceMax(500))
  .force("center", d3.forceCenter(W / 2, H / 2))
  .force("collide", d3.forceCollide(d => d.radius + 12).strength(0.8))
  .alphaDecay(0.025);

// edges
const link = g.append("g").selectAll("line")
  .data(graphData.links)
  .join("line")
  .attr("class", "link")
  .attr("stroke", "#6e7681")
  .attr("stroke-width", d => d.width)
  .on("mouseenter", (e, d) => showTip(e, d.tooltip || d.relationship))
  .on("mouseleave", hideTip)
  .on("mousemove", moveTip);

// nodes
const node = g.append("g").selectAll("g")
  .data(graphData.nodes)
  .join("g")
  .attr("class", "node")
  .call(d3.drag()
    .on("start", (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end", (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }}));

node.append("circle")
  .attr("r", d => d.radius)
  .attr("fill", d => d.color)
  .attr("stroke", "#ffffff")
  .attr("stroke-width", 1.5)
  .attr("filter", "url(#glow)")
  .on("mouseenter", (e, d) => {{ highlightNode(d); showTip(e, d.tooltip); }})
  .on("mouseleave", (e, d) => {{ unhighlightNode(); hideTip(); }})
  .on("mousemove", moveTip);

node.append("text")
  .each(function(d) {{
    const el = d3.select(this);
    const words = d.label.split(" ");
    if (words.length === 1) {{
      el.append("tspan").attr("x", 0).attr("dy", "0").text(d.label);
    }} else {{
      const mid = Math.ceil(words.length / 2);
      el.append("tspan").attr("x", 0).attr("dy", "-0.6em").text(words.slice(0, mid).join(" "));
      el.append("tspan").attr("x", 0).attr("dy", "1.2em").text(words.slice(mid).join(" "));
    }}
  }});

simulation.on("tick", () => {{
  link
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

function highlightNode(d) {{
  const connected = new Set([d.id]);
  graphData.links.forEach(l => {{
    if (l.source.id === d.id) connected.add(l.target.id);
    if (l.target.id === d.id) connected.add(l.source.id);
  }});
  node.select("circle").attr("opacity", n => connected.has(n.id) ? 1 : 0.2);
  link.attr("stroke-opacity", l => (l.source.id === d.id || l.target.id === d.id) ? 0.9 : 0.08)
      .attr("stroke", l => (l.source.id === d.id || l.target.id === d.id) ? "#ffffff" : "#6e7681");
  node.select("text").attr("opacity", n => connected.has(n.id) ? 1 : 0.2);
}}

function unhighlightNode() {{
  node.select("circle").attr("opacity", 1);
  link.attr("stroke-opacity", 0.45).attr("stroke", "#6e7681");
  node.select("text").attr("opacity", 1);
}}

function showTip(e, text) {{
  tooltip.textContent = text;
  tooltip.style.display = "block";
  moveTip(e);
}}
function hideTip() {{ tooltip.style.display = "none"; }}
function moveTip(e) {{
  const x = e.clientX + 14, y = e.clientY - 10;
  tooltip.style.left = (x + 220 > window.innerWidth ? x - 240 : x) + "px";
  tooltip.style.top = y + "px";
}}

simulation.on("end", fitToView);
</script>
</body>
</html>"""
    return html


def render_graph_html(knowledge_graph: nx.Graph, entity_summaries: dict, graph_html_path: str) -> pd.DataFrame:
    import json

    Path(graph_html_path).parent.mkdir(parents=True, exist_ok=True)

    centrality = nx.degree_centrality(knowledge_graph)

    nodes_data = []
    for node_id, attrs in knowledge_graph.nodes(data=True):
        radius = 18 + centrality[node_id] * 44
        nodes_data.append({
            "id": node_id,
            "label": node_id,
            "color": attrs.get("color", "#888888"),
            "radius": round(radius, 1),
            "node_type": attrs.get("node_type", "unknown"),
            "count": attrs.get("count", 0),
            "tooltip": attrs.get("title", node_id).replace("<br>", "\n").replace("<b>", "").replace("</b>", ""),
        })

    weights = [d.get("weight", 1) for _, _, d in knowledge_graph.edges(data=True)]
    max_weight = max(weights) if weights else 1

    edges_data = []
    for src, dst, attrs in knowledge_graph.edges(data=True):
        w = attrs.get("weight", 1)
        edges_data.append({
            "source": src,
            "target": dst,
            "weight": w,
            "width": round(0.8 + (w / max_weight) * 5, 2),
            "relationship": attrs.get("relationship", ""),
            "tooltip": attrs.get("title", "").replace("<br>", "\n"),
        })

    graph_json = json.dumps({"nodes": nodes_data, "links": edges_data})
    html = build_d3_graph_html(graph_json)

    Path(graph_html_path).write_text(html, encoding="utf-8")
    logger.info("Saved D3.js knowledge graph HTML to %s", graph_html_path)

    metadata = pd.DataFrame([
        {
            "node": n,
            "node_type": d.get("node_type", "unknown"),
            "degree": knowledge_graph.degree(n),
            "centrality": round(centrality[n], 4),
            "patient_count": d.get("count", 0),
        }
        for n, d in knowledge_graph.nodes(data=True)
    ]).sort_values("degree", ascending=False)

    return metadata
