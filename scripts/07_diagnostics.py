#!/usr/bin/env python3
"""
07_diagnostics.py — Run structural diagnostics on the citation network.

Reads:
    data/graph/graph.json         — the citation network
    data/graph/metrics.json       — computed network metrics
    data/definitions/_all_definitions.json — extracted definitions
    data/lookup/resolution_log.json       — entity resolution log

Writes:
    data/graph/diagnostics.json   — all diagnostic findings
    data/graph/diagnostics_report.md — human-readable diagnostic report

Diagnostics performed:
    1. Orphan references: citations to abrogated/unknown laws
    2. Hub laws: highest centrality nodes
    3. Isolated laws: very low degree nodes
    4. Cascade analysis: reform impact simulation
    5. Circular dependencies: A→B→A patterns
    6. Definition conflicts: same term, different definitions
    7. Community analysis: regulatory clusters
    8. Regulatory pathway: laws connected to a given topic
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GRAPH_DIR = Path(__file__).parent.parent / "data" / "graph"
DEFINITIONS_DIR = Path(__file__).parent.parent / "data" / "definitions"
LOOKUP_DIR = Path(__file__).parent.parent / "data" / "lookup"

# Known abrogated laws for orphan reference detection
ABROGATED_LAWS = {
    "ley-organica-del-departamento-del-distrito-federal",
    "ley-federal-de-radio-y-television",  # Replaced by LFTR
    "ley-de-vias-generales-de-comunicacion",  # Partially abrogated
    "ley-del-impuesto-empresarial-a-tasa-unica",  # IETU, abrogated 2014
    "ley-del-impuesto-de-depositos-en-efectivo",  # IDE, abrogated 2014
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load graph
# ---------------------------------------------------------------------------

def load_graph_from_json(json_path: Path) -> nx.DiGraph:
    """Reconstruct NetworkX DiGraph from the D3.js JSON format."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    G = nx.DiGraph()

    for node in data.get("nodes", []):
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})

    for link in data.get("links", []):
        G.add_edge(
            link["source"],
            link["target"],
            confidence=link.get("confidence", "medium"),
            citation_count=link.get("citation_count", 1),
        )

    return G


# ---------------------------------------------------------------------------
# Diagnostic 1: Orphan references
# ---------------------------------------------------------------------------

def find_orphan_references(G: nx.DiGraph) -> list[dict]:
    """
    Find citations pointing to laws that:
    - Are not in the canonical laws list (unknown)
    - Are marked as abrogated
    """
    orphans = []
    known_ids = set(CANONICAL_LAWS.keys())

    for source, target, data in G.edges(data=True):
        is_abrogated = target in ABROGATED_LAWS
        is_unknown = target not in known_ids and not G.nodes[target].get("name", "").startswith("Ley")

        if is_abrogated or is_unknown:
            orphans.append({
                "source_law": source,
                "source_name": G.nodes[source].get("name", source),
                "target_law_id": target,
                "target_name": G.nodes.get(target, {}).get("name", target),
                "citation_count": data.get("citation_count", 1),
                "type": "abrogated" if is_abrogated else "unknown",
            })

    return sorted(orphans, key=lambda x: x["citation_count"], reverse=True)


# ---------------------------------------------------------------------------
# Diagnostic 2: Hub laws (most important)
# ---------------------------------------------------------------------------

def identify_hub_laws(G: nx.DiGraph) -> list[dict]:
    """Identify the most structurally central laws."""
    try:
        pagerank = nx.pagerank(G, alpha=0.85)
    except Exception:
        pagerank = {n: 0 for n in G.nodes()}

    betweenness = nx.betweenness_centrality(G)

    results = []
    for node in G.nodes():
        results.append({
            "law_id": node,
            "name": G.nodes[node].get("name", node),
            "short": G.nodes[node].get("short", ""),
            "sector": G.nodes[node].get("sector", ""),
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "pagerank": round(pagerank.get(node, 0), 6),
            "betweenness": round(betweenness.get(node, 0), 6),
            "cascade_score": G.nodes[node].get("cascade_score", 0),
        })

    return sorted(results, key=lambda x: x["pagerank"], reverse=True)[:20]


# ---------------------------------------------------------------------------
# Diagnostic 3: Isolated laws
# ---------------------------------------------------------------------------

def find_isolated_laws(G: nx.DiGraph, threshold: int = 2) -> list[dict]:
    """Find laws with very few connections — potentially obsolete."""
    isolated = []
    for node in G.nodes():
        total_degree = G.in_degree(node) + G.out_degree(node)
        if total_degree <= threshold:
            isolated.append({
                "law_id": node,
                "name": G.nodes[node].get("name", node),
                "sector": G.nodes[node].get("sector", ""),
                "in_degree": G.in_degree(node),
                "out_degree": G.out_degree(node),
                "total_degree": total_degree,
            })

    return sorted(isolated, key=lambda x: x["total_degree"])


# ---------------------------------------------------------------------------
# Diagnostic 4: Cascade analysis
# ---------------------------------------------------------------------------

def compute_cascade_scores(G: nx.DiGraph) -> list[dict]:
    """
    For each law, compute how many other laws would be affected
    if that law were reformed (directly or indirectly).
    """
    G_rev = G.reverse()
    cascade_results = []

    for node in G.nodes():
        # Laws that would be affected = laws that (directly or indirectly) cite this law
        reachable = nx.single_source_shortest_path_length(G_rev, node)
        cascade_size = len(reachable) - 1  # Exclude self

        # Also find direct dependents
        direct_dependents = list(G_rev.successors(node))

        cascade_results.append({
            "law_id": node,
            "name": G.nodes[node].get("name", node),
            "short": G.nodes[node].get("short", ""),
            "sector": G.nodes[node].get("sector", ""),
            "cascade_size": cascade_size,
            "direct_dependents": len(direct_dependents),
            "sample_dependents": direct_dependents[:5],
        })

    return sorted(cascade_results, key=lambda x: x["cascade_size"], reverse=True)[:30]


# ---------------------------------------------------------------------------
# Diagnostic 5: Circular dependencies
# ---------------------------------------------------------------------------

def find_circular_dependencies(G: nx.DiGraph) -> list[dict]:
    """Find laws that mutually cite each other (length-2 cycles) in O(E)."""
    cycles = []
    edges = set(G.edges())
    seen = set()
    for u, v in edges:
        if (v, u) in edges and (v, u) not in seen:
            seen.add((u, v))
            cycle_names = [G.nodes[n].get("name", n)[:50] for n in [u, v]]
            cycles.append({
                "length": 2,
                "law_ids": [u, v],
                "law_names": cycle_names,
                "type": "direct",
            })
    return sorted(cycles, key=lambda x: x["law_ids"])


# ---------------------------------------------------------------------------
# Diagnostic 6: Community analysis
# ---------------------------------------------------------------------------

def analyze_communities(G: nx.DiGraph) -> list[dict]:
    """Analyze the detected regulatory communities/clusters."""
    # Get community assignments from node attributes
    community_map: dict[int, list[str]] = defaultdict(list)
    for node, data in G.nodes(data=True):
        community_id = data.get("community", -1)
        community_map[community_id].append(node)

    communities = []
    for comm_id, members in sorted(community_map.items()):
        if comm_id == -1:
            continue

        # Find the dominant sector in this community
        sectors = Counter(
            G.nodes[m].get("sector", "unknown") for m in members if G.nodes[m].get("sector")
        )
        dominant_sector = sectors.most_common(1)[0][0] if sectors else "mixed"

        # Find the most central member
        try:
            subgraph = G.subgraph(members)
            pr = nx.pagerank(subgraph)
            central_member = max(pr, key=pr.get)
        except Exception:
            central_member = members[0] if members else ""

        communities.append({
            "community_id": comm_id,
            "size": len(members),
            "dominant_sector": dominant_sector,
            "sector_distribution": dict(sectors.most_common(5)),
            "central_law": central_member,
            "central_law_name": G.nodes[central_member].get("name", central_member)[:60] if central_member else "",
            "members": members[:10],  # First 10 members
        })

    return sorted(communities, key=lambda x: x["size"], reverse=True)


# ---------------------------------------------------------------------------
# Diagnostic 7: Definition conflicts
# ---------------------------------------------------------------------------

def load_definition_conflicts() -> list[dict]:
    """Load pre-computed definition conflicts from step 05."""
    all_defs_path = DEFINITIONS_DIR / "_all_definitions.json"
    if not all_defs_path.exists():
        log.warning(f"Definition conflicts file not found: {all_defs_path}")
        return []

    try:
        with open(all_defs_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("top_conflicts", [])
    except Exception as e:
        log.warning(f"Could not load definition conflicts: {e}")
        return []


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_diagnostics_report(diagnostics: dict) -> str:
    """Generate a human-readable Markdown diagnostics report."""
    lines = [
        "# Genoma Regulatorio de México — Diagnóstico Estructural",
        f"\n_Generado: {diagnostics['generated_at']}_",
        "\n---",
        "\n## 1. Referencias Huérfanas",
        f"_(Citas a leyes abrogadas o desconocidas: {len(diagnostics['orphan_references'])} encontradas)_",
        "",
    ]

    for orphan in diagnostics["orphan_references"][:10]:
        lines.append(
            f"- **{orphan['source_name'][:50]}** → `{orphan['target_law_id']}` "
            f"({orphan['citation_count']} referencias, tipo: {orphan['type']})"
        )

    lines += [
        "\n## 2. Leyes Más Centrales (Columnas Vertebrales del Sistema)",
        "_(Ordenadas por PageRank — mayor valor = mayor importancia estructural)_",
        "",
    ]

    for i, hub in enumerate(diagnostics["hub_laws"][:10], 1):
        short = f" ({hub['short']})" if hub.get("short") else ""
        lines.append(
            f"{i}. **{hub['name'][:60]}{short}** — "
            f"PageRank: {hub['pagerank']:.4f}, "
            f"citada por {hub['in_degree']} leyes, "
            f"impacto en cascada: {hub['cascade_score']} leyes"
        )

    lines += [
        "\n## 3. Leyes Aisladas (Posiblemente Obsoletas)",
        f"_(Leyes con 2 o menos conexiones totales: {len(diagnostics['isolated_laws'])} encontradas)_",
        "",
    ]

    for law in diagnostics["isolated_laws"][:10]:
        lines.append(
            f"- **{law['name'][:60]}** — "
            f"In: {law['in_degree']}, Out: {law['out_degree']}"
        )

    lines += [
        "\n## 4. Análisis de Impacto en Cascada",
        "_(¿Cuántas leyes se verían afectadas por una reforma a esta ley?)_",
        "",
    ]

    for i, cascade in enumerate(diagnostics["cascade_analysis"][:10], 1):
        short = f" ({cascade['short']})" if cascade.get("short") else ""
        lines.append(
            f"{i}. **{cascade['name'][:60]}{short}** — "
            f"afecta directamente a {cascade['direct_dependents']} leyes, "
            f"impacto total en {cascade['cascade_size']} leyes"
        )

    lines += [
        "\n## 5. Dependencias Circulares",
        f"_(Grupos de leyes que se referencian mutuamente: {len(diagnostics['circular_dependencies'])} encontrados)_",
        "",
    ]

    for cycle in diagnostics["circular_dependencies"][:10]:
        cycle_str = " → ".join(cycle["law_ids"]) + f" → {cycle['law_ids'][0]}"
        lines.append(f"- `{cycle_str}` (ciclo de {cycle['length']} leyes)")

    lines += [
        "\n## 6. Conflictos de Definiciones",
        f"_(Términos definidos de manera diferente en múltiples leyes: {len(diagnostics['definition_conflicts'])} encontrados)_",
        "",
    ]

    for conflict in diagnostics["definition_conflicts"][:10]:
        laws_str = ", ".join(conflict.get("laws", [])[:3])
        lines.append(
            f"- **\"{conflict['term']}\"**: definido en {conflict['num_laws']} leyes ({laws_str})"
        )

    lines += [
        "\n## 7. Comunidades Regulatorias",
        "_(Grupos de leyes que se citan frecuentemente entre sí)_",
        "",
    ]

    for comm in diagnostics["community_analysis"][:8]:
        lines.append(
            f"- **Cluster {comm['community_id']}** ({comm['size']} leyes) — "
            f"Sector dominante: {comm['dominant_sector']} — "
            f"Ley central: {comm['central_law_name'][:50]}"
        )

    lines += [
        "\n---",
        "\n_Este proyecto es un ejercicio de análisis estructural del marco jurídico mexicano._",
        "_No constituye asesoría legal. Los datos provienen de fuentes públicas y pueden_",
        "_contener errores de extracción._",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=== 07_diagnostics.py — Genoma Regulatorio de México ===")

    json_path = GRAPH_DIR / "graph.json"
    if not json_path.exists():
        log.error(f"Graph JSON not found: {json_path}. Run 06_build_graph.py first.")
        sys.exit(1)

    log.info("Loading graph...")
    G = load_graph_from_json(json_path)
    log.info(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    log.info("Running diagnostics...")

    log.info("  1. Finding orphan references...")
    orphans = find_orphan_references(G)
    log.info(f"     → {len(orphans)} orphan references")

    log.info("  2. Identifying hub laws...")
    hubs = identify_hub_laws(G)

    log.info("  3. Finding isolated laws...")
    isolated = find_isolated_laws(G)
    log.info(f"     → {len(isolated)} isolated laws")

    log.info("  4. Computing cascade scores...")
    cascade = compute_cascade_scores(G)

    log.info("  5. Finding circular dependencies...")
    cycles = find_circular_dependencies(G)
    log.info(f"     → {len(cycles)} circular dependencies")

    log.info("  6. Analyzing communities...")
    communities = analyze_communities(G)
    log.info(f"     → {len(communities)} communities")

    log.info("  7. Loading definition conflicts...")
    def_conflicts = load_definition_conflicts()
    log.info(f"     → {len(def_conflicts)} definition conflicts")

    # Compile diagnostics
    diagnostics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_stats": {
            "num_nodes": G.number_of_nodes(),
            "num_edges": G.number_of_edges(),
        },
        "orphan_references": orphans,
        "hub_laws": hubs,
        "isolated_laws": isolated,
        "cascade_analysis": cascade,
        "circular_dependencies": cycles,
        "community_analysis": communities,
        "definition_conflicts": def_conflicts,
    }

    # Save JSON
    diagnostics_path = GRAPH_DIR / "diagnostics.json"
    with open(diagnostics_path, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, ensure_ascii=False, indent=2)
    log.info(f"Saved diagnostics: {diagnostics_path}")

    # Save Markdown report
    report = generate_diagnostics_report(diagnostics)
    report_path = GRAPH_DIR / "diagnostics_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    log.info(f"Saved report: {report_path}")

    log.info(f"\n=== Diagnostics complete ===")
    log.info(f"  Orphan references: {len(orphans)}")
    log.info(f"  Hub laws identified: {len(hubs)}")
    log.info(f"  Isolated laws: {len(isolated)}")
    log.info(f"  Circular dependencies: {len(cycles)}")
    log.info(f"  Definition conflicts: {len(def_conflicts)}")


if __name__ == "__main__":
    main()
