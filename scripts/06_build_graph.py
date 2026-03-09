#!/usr/bin/env python3
"""
06_build_graph.py — Build the citation network and compute metrics.

Reads:
    data/processed/  — law metadata
    data/citations/  — resolved citations (from steps 03+04)

Writes:
    data/graph/graph.graphml     — NetworkX GraphML for analysis
    data/graph/graph.json        — D3.js-compatible JSON for frontend
    data/graph/metrics.json      — Per-node and summary metrics
    data/graph/graph_summary.md  — Human-readable summary report

Graph structure:
    Nodes: federal laws (id, name, short_name, sector, metrics)
    Edges: citations (source, target, confidence, citation_count)
"""

import json
import logging
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utils.lookup import CANONICAL_LAWS
from scripts.utils.metrics import compute_all_metrics, graph_to_json_format

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
GRAPH_DIR = Path(__file__).parent.parent / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

# Minimum confidence level to include a citation as a graph edge
MIN_CONFIDENCE_FOR_EDGE = "medium"  # "high" | "medium" | "low"
CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_all_laws() -> dict[str, dict]:
    """Load all processed law metadata. Returns {law_id: metadata}."""
    laws: dict[str, dict] = {}

    for path in PROCESSED_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                law = json.load(f)
            law_id = law.get("id", path.stem)
            laws[law_id] = law
        except Exception as e:
            log.warning(f"Could not load {path}: {e}")

    # Also add any known laws not in processed dir (from canonical lookup)
    for law_id, data in CANONICAL_LAWS.items():
        if law_id not in laws:
            laws[law_id] = {
                "id": law_id,
                "name": data["name"],
                "short_name": data.get("short", ""),
                "category": data.get("sector", ""),
                "source_url": data.get("url", ""),
                "num_articles": 0,
                "stub": True,  # Not yet scraped
            }

    log.info(f"Loaded {len(laws)} laws")
    return laws


def load_all_citations() -> list[dict]:
    """Load all resolved citations from the citations directory."""
    all_citations = []

    for path in CITATIONS_DIR.glob("*_citations.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            citations = data.get("citations", [])
            all_citations.extend(citations)
        except Exception as e:
            log.warning(f"Could not load {path}: {e}")

    log.info(f"Loaded {len(all_citations)} citations")
    return all_citations


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(laws: dict[str, dict], citations: list[dict]) -> nx.DiGraph:
    """
    Construct a directed citation network.

    Nodes: laws (with metadata attributes)
    Edges: aggregated citations (multiple citations → single weighted edge)
    """
    G = nx.DiGraph()

    # Add all law nodes
    for law_id, law_data in laws.items():
        G.add_node(
            law_id,
            name=law_data.get("name", ""),
            short=law_data.get("short_name", ""),
            sector=law_data.get("category", ""),
            url=law_data.get("source_url", ""),
            num_articles=law_data.get("num_articles", 0),
            year_enacted=law_data.get("year_enacted"),
            year_last_reform=law_data.get("year_last_reform"),
            stub=law_data.get("stub", False),
        )

    # Aggregate citations into edges
    # Key: (source_law, target_law) → {count, confidence, articles}
    edge_data: dict[tuple, dict] = defaultdict(lambda: {
        "count": 0,
        "max_confidence": "low",
        "articles": [],
    })

    min_rank = CONFIDENCE_RANK[MIN_CONFIDENCE_FOR_EDGE]

    for citation in citations:
        source = citation.get("source_law")
        target = citation.get("target_law_id")
        confidence = citation.get("confidence", "low")

        # Filter by confidence
        if CONFIDENCE_RANK.get(confidence, 0) < min_rank:
            continue

        # Skip unresolved targets
        if not target or target == "unresolved":
            continue

        # Skip self-loops
        if source == target:
            continue

        # Skip if nodes don't exist
        if source not in G or target not in G:
            # Add stub nodes for unknown laws referenced in citations
            if target not in G:
                G.add_node(target, name=target, short="", sector="unknown", stub=True)

        key = (source, target)
        edge_data[key]["count"] += 1

        # Track maximum confidence
        if CONFIDENCE_RANK.get(confidence, 0) > CONFIDENCE_RANK.get(edge_data[key]["max_confidence"], 0):
            edge_data[key]["max_confidence"] = confidence

        # Record a sample article for provenance
        source_article = citation.get("source_article", "")
        if source_article and len(edge_data[key]["articles"]) < 3:
            edge_data[key]["articles"].append(source_article)

    # Add edges to graph
    for (source, target), data in edge_data.items():
        G.add_edge(
            source,
            target,
            confidence=data["max_confidence"],
            citation_count=data["count"],
            sample_article=", ".join(str(a) for a in data["articles"]),
            weight=float(data["count"]),
        )

    log.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def generate_summary_report(G: nx.DiGraph, metrics_result: dict) -> str:
    """Generate a human-readable Markdown summary of the network."""
    summary = metrics_result["summary"]
    node_metrics = metrics_result["node_metrics"]

    lines = [
        "# Genoma Regulatorio de México — Resumen de la Red",
        f"\n_Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "\n## Estadísticas generales",
        f"- **Leyes (nodos):** {summary['num_nodes']:,}",
        f"- **Referencias cruzadas (aristas):** {summary['num_edges']:,}",
        f"- **Densidad de la red:** {summary['density']:.4f}",
        f"- **Comunidades detectadas:** {summary['num_communities']}",
        f"- **Ciclos/dependencias circulares:** {summary['num_cycles']}",
        f"- **Leyes aisladas:** {summary['num_isolated']}",
        "\n## Leyes más centrales (por PageRank)",
        "_Las leyes con mayor PageRank son las 'columnas vertebrales' del sistema jurídico_",
        "",
    ]

    for i, (law_id, score) in enumerate(summary.get("top_hubs", []), 1):
        node_data = G.nodes.get(law_id, {})
        name = node_data.get("name", law_id)[:60]
        short = node_data.get("short", "")
        label = f"{short} — " if short else ""
        lines.append(f"{i}. **{label}{name}** (PageRank: {score:.4f})")

    lines += [
        "\n## Leyes más citadas (por grado de entrada)",
        "_Las leyes más referenciadas por otras leyes_",
        "",
    ]

    for i, (law_id, indegree) in enumerate(summary.get("top_authorities", []), 1):
        node_data = G.nodes.get(law_id, {})
        name = node_data.get("name", law_id)[:60]
        short = node_data.get("short", "")
        label = f"{short} — " if short else ""
        lines.append(f"{i}. **{label}{name}** (citada por {indegree} leyes)")

    lines += [
        "\n## Dependencias circulares (muestra)",
        "_Pares o grupos de leyes que se referencian mutuamente_",
        "",
    ]

    for cycle in summary.get("circular_dependencies", [])[:10]:
        cycle_str = " → ".join(cycle) + f" → {cycle[0]}"
        lines.append(f"- `{cycle_str}`")

    lines += [
        "\n## Nota metodológica",
        "Las citas fueron extraídas mediante expresiones regulares de los textos legales.",
        "La resolución de entidades se realizó mediante coincidencia exacta y similitud de cadenas.",
        "Los resultados deben interpretarse como una primera aproximación estructural,",
        "no como análisis jurídico definitivo.",
        "",
        "_Este proyecto es un ejercicio de análisis estructural del marco jurídico mexicano._",
        "_No constituye asesoría legal. Los datos provienen de fuentes públicas y pueden_",
        "_contener errores de extracción._",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 06_build_graph.py — Genoma Regulatorio de México ===")

    # Load data
    laws = load_all_laws()
    citations = load_all_citations()

    if not citations:
        log.warning("No citations loaded. The graph will have nodes but no edges.")
        log.warning("Run 03_extract_citations.py and 04_resolve_entities.py first.")

    # Build graph
    log.info("Building citation graph...")
    G = build_graph(laws, citations)

    # Compute metrics
    log.info("Computing network metrics...")
    metrics_result = compute_all_metrics(G)

    # Update node attributes in graph with computed metrics
    for node_id, metrics in metrics_result["node_metrics"].items():
        if node_id in G:
            for key, value in metrics.items():
                G.nodes[node_id][key] = value

    # Save GraphML (for NetworkX/Gephi analysis)
    graphml_path = GRAPH_DIR / "graph.graphml"
    nx.write_graphml(G, str(graphml_path))
    log.info(f"Saved GraphML: {graphml_path}")

    # Save D3.js JSON (for frontend)
    json_data = graph_to_json_format(G, metrics_result["node_metrics"])
    json_path = GRAPH_DIR / "graph.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, separators=(",", ":"))
    log.info(f"Saved graph JSON: {json_path} ({json_path.stat().st_size//1024}KB)")

    # Save metrics JSON
    # Convert tuples to lists for JSON serialization
    summary = metrics_result["summary"]
    summary["top_hubs"] = [[k, v] for k, v in summary.get("top_hubs", [])]
    summary["top_authorities"] = [[k, v] for k, v in summary.get("top_authorities", [])]

    metrics_path = GRAPH_DIR / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "node_metrics": metrics_result["node_metrics"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    log.info(f"Saved metrics: {metrics_path}")

    # Save human-readable summary
    report = generate_summary_report(G, metrics_result)
    report_path = GRAPH_DIR / "graph_summary.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    log.info(f"Saved summary report: {report_path}")

    # Print key findings
    s = metrics_result["summary"]
    log.info(f"\n=== Graph complete ===")
    log.info(f"  Nodes: {s['num_nodes']}")
    log.info(f"  Edges: {s['num_edges']}")
    log.info(f"  Density: {s['density']:.4f}")
    log.info(f"  Communities: {s['num_communities']}")
    log.info(f"  Circular dependencies: {s['num_cycles']}")


if __name__ == "__main__":
    main()
