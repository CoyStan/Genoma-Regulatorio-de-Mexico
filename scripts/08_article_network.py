#!/usr/bin/env python3
"""
08_article_network.py — Article-level network metrics and diagnostics.

Each node is a unique article (law_id + article_number).
Each edge is a citation from one article to another law (or a specific article
within that law when target_article is available).

Standard network metrics computed per article:
  - out_degree       : how many laws/articles this article cites
  - in_degree        : how many articles cite this article (if target_article known)
  - citation_count   : raw number of citation instances
  - unique_targets   : number of distinct laws cited from this article
  - law_id           : parent law
  - sector           : parent law sector

Outputs:
  data/graph/article_metrics.json   — per-article metric records
  data/graph/article_metrics.csv    — flat CSV for analysis
  data/graph/article_diagnostics.md — human-readable report
"""

import csv
import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import CANONICAL_LAWS

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
GRAPH_DIR     = Path(__file__).parent.parent / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "unresolved": 0}
MIN_CONFIDENCE  = "low"   # include all resolved citations


def load_citations() -> list[dict]:
    all_cits = []
    for path in CITATIONS_DIR.glob("*_citations.json"):
        try:
            data = json.load(open(path, encoding="utf-8"))
            all_cits.extend(data.get("citations", []))
        except Exception as e:
            log.warning(f"Could not load {path}: {e}")
    log.info(f"Loaded {len(all_cits)} total citations")
    return all_cits


def build_article_graph(citations: list[dict]) -> nx.DiGraph:
    """
    Nodes: '<law_id>::<article>' (e.g. 'codigo-fiscal-de-la-federacion::14-B')
    Edges: source_article → target_article (or target_law when article unknown)
    """
    G = nx.DiGraph()

    for c in citations:
        src_art = str(c.get("source_article") or "").strip()
        if not src_art:
            continue
        src_law = c.get("source_law", "")
        tgt_law = c.get("target_law_id", "")
        if tgt_law in ("unresolved", "", None):
            continue
        if CONFIDENCE_RANK.get(c.get("resolution_confidence", "low"), 0) == 0:
            continue

        src_node = f"{src_law}::{src_art}"
        tgt_art  = str(c.get("target_article") or "").strip()
        tgt_node = f"{tgt_law}::{tgt_art}" if tgt_art else f"{tgt_law}::?"

        # Add nodes with metadata
        for node, law_id in [(src_node, src_law), (tgt_node, tgt_law)]:
            if node not in G:
                canonical = CANONICAL_LAWS.get(law_id, {})
                G.add_node(node,
                    law_id=law_id,
                    article=node.split("::", 1)[1],
                    law_name=canonical.get("name", law_id),
                    sector=canonical.get("sector", "unknown"),
                )

        if G.has_edge(src_node, tgt_node):
            G[src_node][tgt_node]["weight"] += 1
        else:
            G.add_edge(src_node, tgt_node, weight=1,
                       confidence=c.get("resolution_confidence", "low"))

    return G


def compute_article_metrics(G: nx.DiGraph) -> list[dict]:
    log.info("Computing PageRank...")
    try:
        pagerank = nx.pagerank(G, alpha=0.85, weight="weight", max_iter=1000)
    except Exception:
        pagerank = {n: 0.0 for n in G.nodes}

    log.info("Computing betweenness centrality (sampled)...")
    try:
        # Use k-sample for large graphs
        k = min(100, G.number_of_nodes())
        betweenness = nx.betweenness_centrality(G, k=k, weight="weight", normalized=True)
    except Exception:
        betweenness = {n: 0.0 for n in G.nodes}

    records = []
    for node, data in G.nodes(data=True):
        out_deg  = G.out_degree(node, weight="weight")
        in_deg   = G.in_degree(node, weight="weight")
        # unique laws this article cites
        unique_tgt_laws = len({G.nodes[t].get("law_id") for t in G.successors(node)})
        # unique laws that cite this article
        unique_src_laws = len({G.nodes[s].get("law_id") for s in G.predecessors(node)})

        records.append({
            "node_id":           node,
            "law_id":            data.get("law_id", ""),
            "article":           data.get("article", ""),
            "law_name":          data.get("law_name", ""),
            "sector":            data.get("sector", "unknown"),
            "out_degree":        G.out_degree(node),
            "in_degree":         G.in_degree(node),
            "out_weight":        out_deg,
            "in_weight":         in_deg,
            "unique_laws_cited": unique_tgt_laws,
            "unique_laws_citing":unique_src_laws,
            "pagerank":          round(pagerank.get(node, 0.0), 8),
            "betweenness":       round(betweenness.get(node, 0.0), 8),
        })

    records.sort(key=lambda r: r["pagerank"], reverse=True)
    return records


def save_csv(records: list[dict], path: Path):
    if not records:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    log.info(f"Saved CSV: {path} ({len(records)} rows)")


def generate_report(records: list[dict], G: nx.DiGraph) -> str:
    ts = datetime.now(timezone.utc).isoformat()

    # Source articles only (out_degree > 0)
    source_arts = [r for r in records if r["out_degree"] > 0]
    # Target articles only (in_degree > 0, article known)
    cited_arts  = [r for r in records if r["in_degree"] > 0 and r["article"] != "?"]

    # Top by out_degree (most citations sent)
    top_citing = sorted(source_arts, key=lambda r: r["out_weight"], reverse=True)[:10]
    # Top by in_degree (most cited)
    top_cited  = sorted(cited_arts,  key=lambda r: r["in_weight"],  reverse=True)[:10]
    # Top by pagerank
    top_pr     = records[:10]
    # Top by betweenness
    top_bw     = sorted(records, key=lambda r: r["betweenness"], reverse=True)[:10]

    # Law-level summary: citations sent per law
    law_out = Counter()
    law_in  = Counter()
    for r in records:
        law_out[r["law_id"]] += r["out_degree"]
        law_in[r["law_id"]]  += r["in_degree"]

    # Articles with most unique target laws (most diverse citers)
    top_diverse = sorted(source_arts, key=lambda r: r["unique_laws_cited"], reverse=True)[:10]

    lines = [
        "# Genoma Regulatorio de México — Red a Nivel de Artículo",
        f"_Generado: {ts}_",
        "",
        "---",
        "",
        "## Resumen General",
        "",
        f"- **Artículos únicos (nodos):** {G.number_of_nodes():,}",
        f"- **Conexiones entre artículos (aristas):** {G.number_of_edges():,}",
        f"- **Artículos que citan otras leyes:** {len(source_arts):,}",
        f"- **Artículos citados por nombre:** {len(cited_arts):,}",
        f"- **Densidad de red:** {nx.density(G):.5f}",
        "",
        "---",
        "",
        "## 1. Artículos que Más Citan (Mayor out-degree ponderado)",
        "_(Artículos con más referencias a otras leyes)_",
        "",
    ]
    for i, r in enumerate(top_citing, 1):
        lines.append(
            f"{i}. **{r['law_name'] or r['law_id']} — Art. {r['article']}** "
            f"({r['sector']}) — {r['out_weight']} citas salientes, "
            f"{r['unique_laws_cited']} leyes distintas citadas"
        )

    lines += [
        "",
        "---",
        "",
        "## 2. Artículos Más Citados por Nombre (Mayor in-degree ponderado)",
        "_(Artículos específicos referenciados por otras leyes)_",
        "",
    ]
    for i, r in enumerate(top_cited, 1):
        lines.append(
            f"{i}. **{r['law_name'] or r['law_id']} — Art. {r['article']}** "
            f"({r['sector']}) — citado {r['in_weight']} veces desde "
            f"{r['unique_laws_citing']} leyes"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Artículos con Mayor PageRank",
        "_(Importancia estructural — ser citado por artículos influyentes)_",
        "",
    ]
    for i, r in enumerate(top_pr, 1):
        lines.append(
            f"{i}. **{r['law_name'] or r['law_id']} — Art. {r['article']}** "
            f"({r['sector']}) — PageRank: {r['pagerank']:.6f}, "
            f"in: {r['in_degree']}, out: {r['out_degree']}"
        )

    lines += [
        "",
        "---",
        "",
        "## 4. Artículos Puente (Mayor Betweenness Centrality)",
        "_(Artículos que conectan distintas partes del sistema legal)_",
        "",
    ]
    for i, r in enumerate(top_bw, 1):
        lines.append(
            f"{i}. **{r['law_name'] or r['law_id']} — Art. {r['article']}** "
            f"({r['sector']}) — Betweenness: {r['betweenness']:.6f}"
        )

    lines += [
        "",
        "---",
        "",
        "## 5. Artículos con Mayor Diversidad de Citas",
        "_(Artículos que citan el mayor número de leyes distintas)_",
        "",
    ]
    for i, r in enumerate(top_diverse, 1):
        lines.append(
            f"{i}. **{r['law_name'] or r['law_id']} — Art. {r['article']}** "
            f"({r['sector']}) — cita {r['unique_laws_cited']} leyes distintas "
            f"({r['out_weight']} referencias totales)"
        )

    lines += [
        "",
        "---",
        "",
        "## 6. Complejidad por Ley",
        "_(Total de referencias salientes por ley — proxy de complejidad)_",
        "",
    ]
    for law_id, total in law_out.most_common(15):
        canon = CANONICAL_LAWS.get(law_id, {})
        name  = canon.get("name", law_id)[:55]
        lines.append(f"- **{name}** — {total} referencias salientes, {law_in[law_id]} entrantes")

    lines += [
        "",
        "---",
        "_Este análisis opera a nivel de artículo individual._",
        "_Los datos provienen de fuentes públicas y pueden contener errores de extracción._",
    ]

    return "\n".join(lines)


def main():
    log.info("=== 08_article_network.py — Genoma Regulatorio de México ===")

    citations = load_citations()
    if not citations:
        log.error("No citations found. Run steps 03 and 04 first.")
        sys.exit(1)

    log.info("Building article-level graph...")
    G = build_article_graph(citations)
    log.info(f"Article graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    log.info("Computing article-level metrics...")
    records = compute_article_metrics(G)

    # Save JSON
    out_json = GRAPH_DIR / "article_metrics.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    log.info(f"Saved JSON: {out_json} ({len(records)} articles)")

    # Save CSV
    save_csv(records, GRAPH_DIR / "article_metrics.csv")

    # Save diagnostics report
    report = generate_report(records, G)
    report_path = GRAPH_DIR / "article_diagnostics.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    log.info(f"Saved report: {report_path}")

    # Quick summary
    source_arts = [r for r in records if r["out_degree"] > 0]
    log.info("")
    log.info("=== Article network complete ===")
    log.info(f"  Total article nodes : {G.number_of_nodes():,}")
    log.info(f"  Total edges         : {G.number_of_edges():,}")
    log.info(f"  Articles that cite  : {len(source_arts):,}")
    log.info(f"  Output JSON         : {out_json}")
    log.info(f"  Output CSV          : {GRAPH_DIR / 'article_metrics.csv'}")
    log.info(f"  Diagnostics report  : {report_path}")


if __name__ == "__main__":
    main()
