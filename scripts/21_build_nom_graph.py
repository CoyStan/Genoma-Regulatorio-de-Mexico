#!/usr/bin/env python3
"""
21_build_nom_graph.py — Build the NOM graph and the bipartite law→NOM edge list.

Produces three outputs:
  1. data/graph/nom_graph.json       — NOM-only graph (NOMs citing each other)
  2. data/graph/law_nom_edges.json   — Bipartite edges: which laws cite which NOMs
  3. data/graph/law_nom_summary.json — Aggregate stats

Reads:
  data/processed_noms/*.json
  data/nom_citations/*_nom_citations.json
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROCESSED_NOM_DIR = Path(__file__).parent.parent / "data" / "processed_noms"
NOM_CITATIONS_DIR = Path(__file__).parent.parent / "data" / "nom_citations"
GRAPH_DIR         = Path(__file__).parent.parent / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Load NOM nodes ────────────────────────────────────────────────────────────

def load_nom_nodes() -> list[dict]:
    nodes = []
    for path in sorted(PROCESSED_NOM_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                nom = json.load(f)
            nodes.append({
                "id":        nom["id"],
                "nom_code":  nom["nom_code"],
                "name":      nom["name"],
                "short":     nom["nom_code"],
                "ministry":  nom.get("ministry", "unknown"),
                "year":      nom.get("year"),
                "node_type": "nom",
            })
        except Exception as e:
            log.warning(f"Cannot load {path}: {e}")
    return nodes


# ── Load law→NOM citations ────────────────────────────────────────────────────

def load_law_nom_citations() -> list[dict]:
    all_citations = []
    for path in sorted(NOM_CITATIONS_DIR.glob("*_nom_citations.json")):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for c in data.get("citations", []):
                if (c.get("target_nom_id") and
                        c["target_nom_id"] not in ("unresolved", "generic") and
                        c["pattern_name"] == "explicit_nom_code"):
                    all_citations.append(c)
        except Exception:
            pass
    return all_citations


# ── Build bipartite law→NOM edge list ────────────────────────────────────────

def build_law_nom_edges(citations: list[dict]) -> list[dict]:
    """Aggregate law→NOM citations into weighted edges."""
    edge_weights: dict[tuple, int] = Counter()
    for c in citations:
        edge_weights[(c["source_law"], c["target_nom_id"])] += 1

    edges = [
        {
            "source_law": src,
            "target_nom": tgt,
            "weight":     w,
        }
        for (src, tgt), w in sorted(edge_weights.items(), key=lambda x: -x[1])
    ]
    return edges


# ── Build NOM→NOM edges (NOMs citing each other) ─────────────────────────────

def build_nom_nom_edges(nom_nodes: list[dict]) -> list[dict]:
    """
    Find cross-references between NOMs.
    NOMs frequently cite each other in their 'Referencias' section (section 3).
    """
    from scripts.utils.patterns import NOM_CODE_RE_PATTERN  # reuse if available
    nom_ids = {n["id"] for n in nom_nodes}
    nom_code_to_id = {n["nom_code"]: n["id"] for n in nom_nodes}

    nom_code_re = __import__("re").compile(
        r"\b(NOM-\d+[\w]*-[\w\d]+-\d{4})\b", __import__("re").IGNORECASE
    )

    edges = []
    seen = set()

    for path in sorted(PROCESSED_NOM_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                nom = json.load(f)
        except Exception:
            continue

        source_id = nom["id"]
        text = nom.get("full_text", "")

        for m in nom_code_re.finditer(text):
            raw_code = m.group(1).upper()
            target_id = nom_code_to_id.get(raw_code)
            if not target_id or target_id == source_id:
                continue
            key = (source_id, target_id)
            if key not in seen:
                seen.add(key)
                edges.append({"source": source_id, "target": target_id})

    return edges


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=== 21_build_nom_graph.py — Genoma Regulatorio de México ===")

    # NOM nodes
    nom_nodes = load_nom_nodes()
    log.info(f"NOM nodes: {len(nom_nodes)}")

    # NOM→NOM edges
    log.info("Finding NOM→NOM cross-references...")
    nom_edges = build_nom_nom_edges(nom_nodes)
    log.info(f"  NOM→NOM edges: {len(nom_edges)}")

    # NOM graph JSON
    nom_graph = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes":        nom_nodes,
        "edges":        nom_edges,
        "num_nodes":    len(nom_nodes),
        "num_edges":    len(nom_edges),
        "note":         "Nodos = NOMs vigentes (2013+). Aristas = referencias cruzadas entre NOMs.",
    }
    nom_graph_path = GRAPH_DIR / "nom_graph.json"
    with open(nom_graph_path, "w", encoding="utf-8") as f:
        json.dump(nom_graph, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {nom_graph_path}")

    # Bipartite law→NOM edges
    law_nom_citations = load_law_nom_citations()
    law_nom_edges     = build_law_nom_edges(law_nom_citations)
    log.info(f"Law→NOM edges: {len(law_nom_edges)}")

    # Top cited NOMs
    nom_indegree = Counter(e["target_nom"] for e in law_nom_edges)
    top_noms = nom_indegree.most_common(20)

    # Laws with most NOM citations
    law_outdegree = Counter(e["source_law"] for e in law_nom_edges)
    top_laws = law_outdegree.most_common(20)

    # Ministry breakdown
    nom_id_to_ministry = {n["id"]: n["ministry"] for n in nom_nodes}
    ministry_counts = Counter(
        nom_id_to_ministry.get(e["target_nom"], "unknown")
        for e in law_nom_edges
    )

    law_nom_output = {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "total_edges":     len(law_nom_edges),
        "edges":           law_nom_edges,
    }
    law_nom_path = GRAPH_DIR / "law_nom_edges.json"
    with open(law_nom_path, "w", encoding="utf-8") as f:
        json.dump(law_nom_output, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {law_nom_path}")

    summary = {
        "generated_at":        datetime.now(timezone.utc).isoformat(),
        "num_noms":            len(nom_nodes),
        "nom_nom_edges":       len(nom_edges),
        "law_nom_edges":       len(law_nom_edges),
        "laws_citing_noms":    len(set(e["source_law"] for e in law_nom_edges)),
        "noms_cited_by_laws":  len(set(e["target_nom"] for e in law_nom_edges)),
        "top_cited_noms":      [{"nom_id": k, "cited_by_n_laws": v} for k, v in top_noms],
        "top_laws_citing_noms": [{"law_id": k, "noms_cited": v} for k, v in top_laws],
        "citations_by_ministry": dict(ministry_counts.most_common()),
    }
    summary_path = GRAPH_DIR / "law_nom_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    log.info(f"Saved: {summary_path}")

    log.info(f"\n=== NOM graph complete ===")
    log.info(f"  NOMs: {len(nom_nodes)}")
    log.info(f"  NOM→NOM edges: {len(nom_edges)}")
    log.info(f"  Law→NOM edges: {len(law_nom_edges)}")
    log.info(f"  Laws citing NOMs: {len(set(e['source_law'] for e in law_nom_edges))}")
    log.info(f"  NOMs cited by laws: {len(set(e['target_nom'] for e in law_nom_edges))}")


if __name__ == "__main__":
    main()
