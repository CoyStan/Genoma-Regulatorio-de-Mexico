#!/usr/bin/env python3
"""
08_visualize_articles.py — Static article-level citation network visualization.

Focuses on the top N laws by PageRank and renders their articles as nodes,
grouped by law, colored by sector. Edges represent citation relationships
between articles across laws.

Outputs: data/graph/article_network.png  (high-res)
         data/graph/article_network.svg
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOP_LAWS = 16          # Number of most-central laws to include
MIN_EDGE_CONF = {"high", "medium"}  # Edge confidence filter
FIG_SIZE = (28, 24)
DPI = 200
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "graph"

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
GRAPH_JSON    = Path(__file__).parent.parent / "data" / "graph" / "graph.json"
METRICS_JSON  = Path(__file__).parent.parent / "data" / "graph" / "metrics.json"

# ---------------------------------------------------------------------------
# Sector color palette (colorblind-friendly)
# ---------------------------------------------------------------------------

SECTOR_COLORS = {
    "constitucional":       "#E63946",  # red
    "penal":                "#F4A261",  # orange
    "fiscal":               "#2A9D8F",  # teal
    "financiero":           "#457B9D",  # steel blue
    "administrativo":       "#6A4C93",  # purple
    "trabajo":              "#F77F00",  # amber
    "salud":                "#E9C46A",  # yellow-gold
    "ambiental":            "#52B788",  # green
    "educacion":            "#90BE6D",  # lime
    "energia":              "#FF6B6B",  # coral
    "seguridad":            "#4D908E",  # dark teal
    "militar":              "#577590",  # slate
    "agrario":              "#A8C5DA",  # light blue
    "mercantil":            "#C77DFF",  # violet
    "electoral":            "#F9C74F",  # gold
    "anticorrupcion":       "#43AA8B",  # mint
    "migracion":            "#B5838D",  # mauve
    "social":               "#F28482",  # rose
    "propiedad-intelectual":"#84A98C",  # sage
    "telecomunicaciones":   "#6D6875",  # dusty purple
    "competencia":          "#B7B7A4",  # warm grey
    "civil":                "#A2D2FF",  # sky blue
    "unknown":              "#CCCCCC",  # grey
}

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_top_laws(n: int) -> list[dict]:
    """Return the top N laws by PageRank from graph.json."""
    with open(GRAPH_JSON) as f:
        graph = json.load(f)
    nodes = sorted(graph["nodes"], key=lambda x: x.get("pagerank", 0), reverse=True)
    return nodes[:n]

def load_article_citations(top_law_ids: set[str]) -> list[dict]:
    """
    Load all citations where the TARGET law is one of the top laws.
    Source law can be any law in the corpus (creates richer connections).
    Both source and target are kept; we'll add stub source nodes colored
    by their sector.
    """
    citations = []
    for path in CITATIONS_DIR.glob("*_citations.json"):
        with open(path) as f:
            data = json.load(f)
        src_law = data.get("law_id", path.stem)
        for c in data.get("citations", []):
            tgt_law = c.get("target_law_id")
            if not tgt_law or tgt_law == "unresolved":
                continue
            if tgt_law not in top_law_ids:
                continue
            if c.get("confidence", "medium") not in MIN_EDGE_CONF:
                continue
            citations.append({
                "src_law":  src_law,
                "src_art":  c.get("source_article", "?"),
                "tgt_law":  tgt_law,
                "tgt_art":  c.get("target_article"),
                "confidence": c.get("confidence", "medium"),
                "src_in_top": src_law in top_law_ids,
            })
    return citations

# ---------------------------------------------------------------------------
# Build article-level graph
# ---------------------------------------------------------------------------

def build_article_graph(top_laws: list[dict], citations: list[dict], all_law_sectors: dict):
    """Build a NetworkX DiGraph at article level."""
    G = nx.DiGraph()

    law_meta = {n["id"]: n for n in top_laws}

    # Add article nodes for ALL citation participants
    for c in citations:
        # Source node
        src_id = f"{c['src_law']}::{c['src_art']}"
        if src_id not in G:
            if c["src_law"] in law_meta:
                meta = law_meta[c["src_law"]]
                G.add_node(src_id, law=c["src_law"], article=c["src_art"],
                           sector=meta.get("sector", "unknown"),
                           law_name=meta.get("name", c["src_law"]),
                           law_short=meta.get("short", c["src_law"][:15]),
                           in_top=True)
            else:
                # Stub node from external law
                sector = all_law_sectors.get(c["src_law"], "unknown")
                G.add_node(src_id, law=c["src_law"], article=c["src_art"],
                           sector=sector,
                           law_name=c["src_law"],
                           law_short=c["src_law"][:15],
                           in_top=False)

        # Target node (always in top laws)
        tgt_art = c.get("tgt_art") or "?"
        tgt_id = f"{c['tgt_law']}::{tgt_art}"
        if tgt_id not in G:
            meta = law_meta[c["tgt_law"]]
            G.add_node(tgt_id, law=c["tgt_law"], article=tgt_art,
                       sector=meta.get("sector", "unknown"),
                       law_name=meta.get("name", c["tgt_law"]),
                       law_short=meta.get("short", c["tgt_law"][:15]),
                       in_top=True)

    # Add edges
    for c in citations:
        tgt_art = c.get("tgt_art") or "?"
        src_node = f"{c['src_law']}::{c['src_art']}"
        tgt_node = f"{c['tgt_law']}::{tgt_art}"
        if src_node in G and tgt_node in G and src_node != tgt_node:
            if G.has_edge(src_node, tgt_node):
                G[src_node][tgt_node]["weight"] += 1
            else:
                G.add_edge(src_node, tgt_node, weight=1, confidence=c["confidence"])

    return G

# ---------------------------------------------------------------------------
# Layout: arrange laws in a circle, articles spread around each law center
# ---------------------------------------------------------------------------

def compute_layout(G: nx.DiGraph, top_laws: list[dict]) -> dict:
    """
    Inner ring: top-law article clusters.
    Outer ring: stub nodes from external source laws.
    """
    top_law_ids = [n["id"] for n in top_laws]
    n_laws = len(top_law_ids)

    # Inner ring: positions of top-law centers
    law_centers = {}
    inner_r = 7.5
    for i, law_id in enumerate(top_law_ids):
        angle = 2 * math.pi * i / n_laws - math.pi / 2
        law_centers[law_id] = (inner_r * math.cos(angle), inner_r * math.sin(angle))

    # Group nodes by law
    top_law_nodes = defaultdict(list)
    stub_nodes = []
    for node in G.nodes():
        if G.nodes[node]["in_top"]:
            top_law_nodes[G.nodes[node]["law"]].append(node)
        else:
            stub_nodes.append(node)

    pos = {}

    # Place top-law article clusters
    for law_id, nodes in top_law_nodes.items():
        cx, cy = law_centers[law_id]
        n = len(nodes)
        if n == 1:
            pos[nodes[0]] = (cx, cy)
        else:
            sub = G.subgraph(nodes)
            try:
                sub_pos = nx.spring_layout(sub, k=0.5, iterations=80, seed=42)
            except Exception:
                sub_pos = {nd: (0, 0) for nd in nodes}
            xs = [p[0] for p in sub_pos.values()]
            ys = [p[1] for p in sub_pos.values()]
            scale = min(2.2, max(0.8, n / 12))
            cx_off = sum(xs) / len(xs)
            cy_off = sum(ys) / len(ys)
            for nd, (x, y) in sub_pos.items():
                pos[nd] = (cx + (x - cx_off) * scale, cy + (y - cy_off) * scale)

    # Place stub nodes on outer ring, grouped by their target law
    # Find which top law each stub node points to
    stub_by_target = defaultdict(list)
    for nd in stub_nodes:
        # find this stub's target(s)
        targets = [v for _, v in G.out_edges(nd) if G.nodes[v]["in_top"]]
        if targets:
            stub_by_target[G.nodes[targets[0]]["law"]].append(nd)
        else:
            stub_by_target["__misc__"].append(nd)

    outer_r = 13.5
    for target_law, snodes in stub_by_target.items():
        if target_law == "__misc__":
            base_angle = 0
        else:
            cx, cy = law_centers.get(target_law, (0, 0))
            base_angle = math.atan2(cy, cx)
        n = len(snodes)
        for j, nd in enumerate(snodes):
            spread = 0.25 * (j - n / 2) / max(n, 1)
            angle = base_angle + spread
            jitter_r = outer_r + np.random.default_rng(hash(nd) % 2**32).uniform(-0.5, 0.5)
            pos[nd] = (jitter_r * math.cos(angle), jitter_r * math.sin(angle))

    return pos, law_centers

# ---------------------------------------------------------------------------
# Draw
# ---------------------------------------------------------------------------

def draw(G: nx.DiGraph, pos: dict, law_centers: dict, top_laws: list[dict],
         out_png: Path, out_svg: Path) -> None:

    fig, ax = plt.subplots(figsize=FIG_SIZE, facecolor="#0F0F1A")
    ax.set_facecolor("#0F0F1A")
    ax.axis("off")

    nodes = list(G.nodes())
    node_colors = [SECTOR_COLORS.get(G.nodes[n]["sector"], "#CCCCCC") for n in nodes]

    # Node size: top-law articles larger; stub nodes small
    degrees = dict(G.degree())
    node_sizes = []
    for n in nodes:
        d = degrees.get(n, 0)
        if G.nodes[n]["in_top"]:
            node_sizes.append(max(25, min(180, 25 + d * 10)))
        else:
            node_sizes.append(max(8, min(40, 8 + d * 4)))

    # Draw law cluster backgrounds (soft glow circles)
    law_meta = {n["id"]: n for n in top_laws}
    law_article_counts = defaultdict(int)
    for nd in G.nodes():
        law_article_counts[G.nodes[nd]["law"]] += 1

    for law_id, (cx, cy) in law_centers.items():
        if law_id not in law_meta:
            continue
        meta = law_meta[law_id]
        color = SECTOR_COLORS.get(meta.get("sector", "unknown"), "#CCCCCC")
        count = law_article_counts.get(law_id, 1)
        r = 0.5 + count * 0.04
        circle = plt.Circle((cx, cy), r, color=color, alpha=0.07, zorder=1)
        ax.add_patch(circle)
        circle2 = plt.Circle((cx, cy), r * 0.6, color=color, alpha=0.05, zorder=1)
        ax.add_patch(circle2)

    # Draw edges
    edge_list = list(G.edges())
    edge_colors = []
    edge_alphas = []
    for u, v in edge_list:
        conf = G[u][v].get("confidence", "medium")
        if conf == "high":
            edge_colors.append("#FFFFFF")
            edge_alphas.append(0.25)
        else:
            edge_colors.append("#8899AA")
            edge_alphas.append(0.12)

    # Draw edges in batches by alpha for performance
    for (u, v), color, alpha in zip(edge_list, edge_colors, edge_alphas):
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        ax.annotate(
            "", xy=(x1, y1), xytext=(x0, y0),
            arrowprops=dict(
                arrowstyle="-|>",
                color=color,
                alpha=alpha,
                lw=0.4,
                mutation_scale=5,
                connectionstyle="arc3,rad=0.05",
            ),
            zorder=2,
        )

    # Draw nodes
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.85,
        linewidths=0.3,
        edgecolors="#FFFFFF",
    )

    # Law labels — placed slightly above each cluster center, larger & readable
    for law_id, (cx, cy) in law_centers.items():
        if law_id not in law_meta:
            continue
        meta = law_meta[law_id]
        short = meta.get("short", "") or meta.get("name", law_id)[:18]
        color = SECTOR_COLORS.get(meta.get("sector", "unknown"), "#CCCCCC")
        # Offset label toward the outside of the circle
        angle = math.atan2(cy, cx)
        lx = cx + 0.9 * math.cos(angle)
        ly = cy + 0.9 * math.sin(angle)
        ax.text(lx, ly, short, fontsize=8, ha="center", va="center",
                color="white", fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.35", facecolor=color,
                          edgecolor="white", alpha=0.85, linewidth=0.8))

    # Legend: sectors present
    sectors_present = sorted(set(G.nodes[n]["sector"] for n in G.nodes()))
    legend_patches = [
        mpatches.Patch(color=SECTOR_COLORS.get(s, "#CCC"), label=s.replace("-", " ").title())
        for s in sectors_present
    ]
    legend = ax.legend(
        handles=legend_patches, loc="lower left",
        fontsize=7, framealpha=0.2, facecolor="#1A1A2E",
        edgecolor="#444466", labelcolor="white",
        title="Sector", title_fontsize=8,
        ncol=2,
    )
    legend.get_title().set_color("white")

    # Title
    ax.set_title(
        f"Genoma Regulatorio de México — Red de Citas a Nivel Artículo\n"
        f"Top {len(top_laws)} leyes · {G.number_of_nodes()} artículos · {G.number_of_edges()} conexiones",
        color="white", fontsize=13, fontweight="bold", pad=14,
    )

    plt.tight_layout(pad=1.0)
    fig.savefig(out_png, dpi=DPI, bbox_inches="tight", facecolor="#0F0F1A")
    fig.savefig(out_svg, format="svg", bbox_inches="tight", facecolor="#0F0F1A")
    plt.close(fig)
    print(f"Saved: {out_png}")
    print(f"Saved: {out_svg}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Loading top {TOP_LAWS} laws by PageRank...")
    top_laws = load_top_laws(TOP_LAWS)
    top_law_ids = {n["id"] for n in top_laws}
    print(f"  Laws: {', '.join(n.get('short', n['id'][:15]) for n in top_laws)}")

    # Build sector lookup for all laws in graph
    with open(GRAPH_JSON) as f:
        all_nodes = json.load(f)["nodes"]
    all_law_sectors = {n["id"]: n.get("sector", "unknown") for n in all_nodes}

    print("Loading article-level citations (all sources → top laws)...")
    citations = load_article_citations(top_law_ids)
    print(f"  Total citations into top laws: {len(citations)}")

    print("Building article graph...")
    G = build_article_graph(top_laws, citations, all_law_sectors)
    print(f"  Nodes (articles): {G.number_of_nodes()}")
    print(f"  Edges (citations): {G.number_of_edges()}")

    print("Computing layout...")
    pos, law_centers = compute_layout(G, top_laws)

    out_png = OUTPUT_DIR / "article_network.png"
    out_svg = OUTPUT_DIR / "article_network.svg"
    print("Drawing...")
    draw(G, pos, law_centers, top_laws, out_png, out_svg)
    print("Done.")


if __name__ == "__main__":
    main()
