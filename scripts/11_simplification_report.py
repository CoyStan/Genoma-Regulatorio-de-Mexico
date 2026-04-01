#!/usr/bin/env python3
"""
11_simplification_report.py — Identify laws that could be removed, merged, or reformed
to reduce complexity in the Mexican federal legal system.

Reads:  data/graph/graph.json
        data/graph/diagnostics.json
        data/definitions/_all_definitions.json

Writes: data/graph/simplification.json
        data/graph/simplification_report.md
"""

import json
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

GRAPH_DIR = Path(__file__).parent.parent / "data" / "graph"
DEFS_DIR  = Path(__file__).parent.parent / "data" / "definitions"

# -----------------------------------------------------------------------
# Load data
# -----------------------------------------------------------------------

def load_data():
    with open(GRAPH_DIR / "graph.json", encoding="utf-8") as f:
        graph = json.load(f)
    with open(GRAPH_DIR / "diagnostics.json", encoding="utf-8") as f:
        diag = json.load(f)

    nodes = {n["id"]: n for n in graph["nodes"]}
    links = graph["links"]

    # Build adjacency
    out_edges = defaultdict(list)  # law → [targets]
    in_edges  = defaultdict(list)  # law → [sources]
    for l in links:
        s = l["source"] if isinstance(l["source"], str) else l["source"]["id"]
        t = l["target"] if isinstance(l["target"], str) else l["target"]["id"]
        out_edges[s].append(t)
        in_edges[t].append(s)

    # Definition conflicts
    all_defs_path = DEFS_DIR / "_all_definitions.json"
    def_conflicts = []
    conflict_laws = Counter()   # law_id → number of conflicting definitions it contributes to
    if all_defs_path.exists():
        with open(all_defs_path, encoding="utf-8") as f:
            defs = json.load(f)
        for conflict in defs.get("top_conflicts", []):
            def_conflicts.append(conflict)
            for law in conflict.get("laws", []):
                conflict_laws[law] += 1

    # Circular dependency involvement
    cycle_laws = Counter()
    for cycle in diag.get("circular_dependencies", []):
        for law_id in cycle.get("law_ids", []):
            cycle_laws[law_id] += 1

    return nodes, out_edges, in_edges, diag, def_conflicts, conflict_laws, cycle_laws


# -----------------------------------------------------------------------
# 1. Removal candidates — safe to abrogate
# -----------------------------------------------------------------------

def removal_candidates(nodes, in_edges, out_edges, cycle_laws):
    """
    A law is a removal candidate if:
    - Few laws depend on it (low in_degree)
    - It doesn't sit in circular dependencies (low coupling)
    - Low cascade score (removing it won't break many others)
    Score: weighted combination, normalized 0-100.
    """
    results = []
    for law_id, meta in nodes.items():
        if meta.get("stub"):
            continue
        ind  = meta.get("in_degree", 0)
        outd = meta.get("out_degree", 0)
        casc = meta.get("cascade_score", 0)
        cycs = cycle_laws.get(law_id, 0)

        # Penalty: high in-degree, cascade, cycles = harder to remove
        # All are 0-good, higher = harder to remove
        max_in   = 316  # CPEUM
        max_casc = 317
        max_cyc  = max(cycle_laws.values()) if cycle_laws else 1

        safety = (
            (1 - ind   / max_in)   * 50 +
            (1 - casc  / max_casc) * 35 +
            (1 - cycs  / max_cyc)  * 15
        )

        results.append({
            "law_id":       law_id,
            "name":         meta.get("name", law_id),
            "short":        meta.get("short", ""),
            "sector":       meta.get("sector", "unknown"),
            "in_degree":    ind,
            "out_degree":   outd,
            "cascade_score": casc,
            "cycle_count":  cycs,
            "removal_safety_score": round(safety, 1),
            "rationale": _removal_rationale(ind, outd, casc, cycs),
        })

    return sorted(results, key=lambda x: x["removal_safety_score"], reverse=True)


def _removal_rationale(ind, outd, casc, cycs):
    parts = []
    if ind == 0:
        parts.append("ninguna ley la cita")
    elif ind <= 3:
        parts.append(f"solo {ind} ley(es) la citan")
    if casc <= 5:
        parts.append("impacto en cascada mínimo")
    if cycs == 0:
        parts.append("sin dependencias circulares")
    if outd <= 5:
        parts.append(f"cita solo {outd} leyes (bajo acoplamiento)")
    return "; ".join(parts) if parts else "baja actividad general"


# -----------------------------------------------------------------------
# 2. Merger candidates — laws that could be consolidated
# -----------------------------------------------------------------------

def merger_candidates(nodes, in_edges, out_edges, cycle_laws):
    """
    Two laws are merger candidates if they:
    - Are in the same sector
    - Mutually cite each other (circular dependency)
    - Both have low in-degree from outside their sector
    Score by mutual citation density.
    """
    # Find mutual pairs
    all_edges = set()
    for src, targets in out_edges.items():
        for tgt in targets:
            all_edges.add((src, tgt))

    pairs = []
    seen = set()
    for (src, tgt) in all_edges:
        if (tgt, src) in all_edges and (tgt, src) not in seen:
            seen.add((src, tgt))
            src_meta = nodes.get(src, {})
            tgt_meta = nodes.get(tgt, {})
            if src_meta.get("stub") or tgt_meta.get("stub"):
                continue

            same_sector = src_meta.get("sector") == tgt_meta.get("sector")
            src_in = src_meta.get("in_degree", 0)
            tgt_in = tgt_meta.get("in_degree", 0)
            src_out = out_edges.get(src, [])
            tgt_out = out_edges.get(tgt, [])

            # How much do they reference each other relative to total references?
            mutual_density = 2 / max(len(src_out) + len(tgt_out), 1)

            merger_score = (
                (30 if same_sector else 0) +
                min(40, mutual_density * 400) +
                max(0, 20 - (src_in + tgt_in) // 4) +
                (10 if cycle_laws.get(src, 0) > 0 and cycle_laws.get(tgt, 0) > 0 else 0)
            )

            pairs.append({
                "law_a":        src,
                "name_a":       src_meta.get("name", src)[:70],
                "short_a":      src_meta.get("short", ""),
                "law_b":        tgt,
                "name_b":       tgt_meta.get("name", tgt)[:70],
                "short_b":      tgt_meta.get("short", ""),
                "sector":       src_meta.get("sector", "mixed"),
                "same_sector":  same_sector,
                "merger_score": round(merger_score, 1),
                "rationale": _merger_rationale(same_sector, src_in, tgt_in),
            })

    return sorted(pairs, key=lambda x: x["merger_score"], reverse=True)[:40]


def _merger_rationale(same_sector, src_in, tgt_in):
    parts = ["se citan mutuamente"]
    if same_sector:
        parts.append("mismo sector jurídico")
    if src_in + tgt_in < 20:
        parts.append("baja dependencia externa")
    return "; ".join(parts)


# -----------------------------------------------------------------------
# 3. Reform priority — most complex, most conflicting
# -----------------------------------------------------------------------

def reform_priority(nodes, cycle_laws, conflict_laws, in_edges):
    """
    Laws that need reform (not removal) because they're heavily used
    but also contribute heavily to definitional ambiguity and circular coupling.
    """
    results = []
    for law_id, meta in nodes.items():
        if meta.get("stub"):
            continue
        ind   = meta.get("in_degree", 0)
        casc  = meta.get("cascade_score", 0)
        cycs  = cycle_laws.get(law_id, 0)
        conf  = conflict_laws.get(law_id, 0)

        # Must be important enough to reform (not just delete)
        importance = ind + casc // 10

        complexity_score = (
            cycs  * 15 +   # circular dependencies
            conf  * 20 +   # definition conflicts
            min(30, importance // 5)  # weight by importance
        )

        if complexity_score < 10:
            continue

        results.append({
            "law_id":             law_id,
            "name":               meta.get("name", law_id),
            "short":              meta.get("short", ""),
            "sector":             meta.get("sector", "unknown"),
            "in_degree":          ind,
            "cascade_score":      casc,
            "circular_deps":      cycs,
            "definition_conflicts": conf,
            "complexity_score":   round(complexity_score, 1),
            "rationale":          _reform_rationale(cycs, conf, ind),
        })

    return sorted(results, key=lambda x: x["complexity_score"], reverse=True)[:40]


def _reform_rationale(cycs, conf, ind):
    parts = []
    if cycs > 0:
        parts.append(f"involucrada en {cycs} dependencia(s) circular(es)")
    if conf > 0:
        parts.append(f"aporta {conf} término(s) con definición conflictiva")
    if ind > 30:
        parts.append(f"citada por {ind} leyes — reforma tendría alto impacto")
    return "; ".join(parts)


# -----------------------------------------------------------------------
# 4. Summary statistics
# -----------------------------------------------------------------------

def compute_summary(nodes, removal, mergers, reform, in_edges):
    corpus_laws = [n for n in nodes.values() if not n.get("stub")]
    isolated = [r for r in removal if r["in_degree"] == 0 and r["out_degree"] <= 2]
    low_conn  = [r for r in removal if r["removal_safety_score"] >= 85 and r not in isolated]

    return {
        "total_laws":          len(corpus_laws),
        "removal_candidates":  len([r for r in removal if r["removal_safety_score"] >= 80]),
        "isolated_laws":       len(isolated),
        "merger_pairs":        len(mergers),
        "reform_priority":     len(reform),
        "potential_reduction": f"{len([r for r in removal if r['removal_safety_score'] >= 80])} leyes ({round(len([r for r in removal if r['removal_safety_score'] >= 80])/len(corpus_laws)*100)}% del corpus)",
    }


# -----------------------------------------------------------------------
# Report generation
# -----------------------------------------------------------------------

def generate_report(summary, removal, mergers, reform, def_conflicts):
    lines = [
        "# Genoma Regulatorio de México — Reporte de Simplificación",
        f"\n_Generado: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}_",
        "\n---",
        "\n## Resumen Ejecutivo",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Leyes en el corpus | {summary['total_laws']} |",
        f"| Candidatas a abrogación | {summary['removal_candidates']} |",
        f"| Leyes aisladas (0 vínculos) | {summary['isolated_laws']} |",
        f"| Pares candidatos a fusión | {summary['merger_pairs']} |",
        f"| Leyes que requieren reforma urgente | {summary['reform_priority']} |",
        f"| Reducción potencial del corpus | {summary['potential_reduction']} |",
        "",
        "> **Lectura:** Una ley candidata a abrogación tiene bajo impacto en cascada — su eliminación no requeriría reformar muchas otras leyes. Una ley candidata a fusión se solapa funcionalmente con otra del mismo sector.",

        "\n---",
        "\n## 1. Candidatas a Abrogación",
        "_Leyes con bajo impacto en cascada, pocas dependencias y escasa relevancia sistémica._",
        "_Score de seguridad: 0 = difícil de eliminar (CPEUM), 100 = completamente aislada._",
        "",
        "| # | Ley | Sector | Citada por | Cascada | Score | Razón |",
        "|---|-----|--------|-----------|---------|-------|-------|",
    ]

    for i, r in enumerate([x for x in removal if x["removal_safety_score"] >= 80][:30], 1):
        short = r["short"] or r["name"][:30]
        lines.append(
            f"| {i} | **{short}** | {r['sector']} | {r['in_degree']} | {r['cascade_score']} | {r['removal_safety_score']} | {r['rationale']} |"
        )

    lines += [
        "\n## 2. Candidatas a Fusión",
        "_Pares de leyes que se citan mutuamente y comparten sector — podrían consolidarse en un solo instrumento._",
        "",
        "| # | Ley A | Ley B | Sector | Score | Razón |",
        "|---|-------|-------|--------|-------|-------|",
    ]

    for i, m in enumerate(mergers[:20], 1):
        a = m["short_a"] or m["name_a"][:25]
        b = m["short_b"] or m["name_b"][:25]
        lines.append(
            f"| {i} | **{a}** | **{b}** | {m['sector']} | {m['merger_score']} | {m['rationale']} |"
        )

    lines += [
        "\n## 3. Reforma Urgente (Alta Complejidad)",
        "_Leyes muy referenciadas que concentran ambigüedad: definiciones conflictivas y dependencias circulares._",
        "_No conviene abrogarlas — conviene clarificarlas y desambiguarlas._",
        "",
        "| # | Ley | Sector | Dep. Circulares | Conflictos def. | Score |",
        "|---|-----|--------|----------------|-----------------|-------|",
    ]

    for i, r in enumerate(reform[:20], 1):
        short = r["short"] or r["name"][:35]
        lines.append(
            f"| {i} | **{short}** | {r['sector']} | {r['circular_deps']} | {r['definition_conflicts']} | {r['complexity_score']} |"
        )

    lines += [
        "\n## 4. Términos con Definición Conflictiva",
        "_Términos clave definidos de forma diferente en múltiples leyes — fuente de ambigüedad jurídica._",
        "",
        "| Término | # Leyes | Leyes |",
        "|---------|---------|-------|",
    ]

    for c in def_conflicts[:15]:
        laws_str = ", ".join(c.get("laws", [])[:4])
        lines.append(f"| **\"{c['term']}\"** | {c['num_laws']} | {laws_str} |")

    lines += [
        "\n---",
        "\n## Metodología",
        "",
        "- **Score de abrogación** (0–100): pondera in-degree (50%), cascade score (35%) y dependencias circulares (15%). Mayor score = más seguro abrogar.",
        "- **Score de fusión** (0–100): pondera citación mutua, mismo sector y baja dependencia externa.",
        "- **Score de complejidad** (reforma): suma dependencias circulares × 15 + conflictos de definición × 20.",
        "- Fuente: red de 318 leyes federales, 4,534 aristas, 10,844 citas totales.",
        "",
        "_Este análisis es exploratorio. Toda decisión de abrogación o fusión requiere revisión jurídica experta._",
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main():
    print("Loading data...")
    nodes, out_edges, in_edges, diag, def_conflicts, conflict_laws, cycle_laws = load_data()

    print("Computing removal candidates...")
    removal = removal_candidates(nodes, in_edges, out_edges, cycle_laws)

    print("Computing merger candidates...")
    mergers = merger_candidates(nodes, in_edges, out_edges, cycle_laws)

    print("Computing reform priority...")
    reform  = reform_priority(nodes, cycle_laws, conflict_laws, in_edges)

    print("Computing summary...")
    summary = compute_summary(nodes, removal, mergers, reform, in_edges)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "removal_candidates":  removal[:50],
        "merger_candidates":   mergers,
        "reform_priority":     reform,
        "definition_conflicts": def_conflicts[:20],
    }

    out_json = GRAPH_DIR / "simplification.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved: {out_json}")

    report = generate_report(summary, removal, mergers, reform, def_conflicts)
    out_md = GRAPH_DIR / "simplification_report.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Saved: {out_md}")

    print("\n=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
