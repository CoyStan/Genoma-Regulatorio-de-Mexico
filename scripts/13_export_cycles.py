#!/usr/bin/env python3
"""
13_export_cycles.py — Export mutual citation pairs (circular dependencies)
with the exact citation text from both directions for manual diagnosis.

Reads:  data/citations/<law_id>_citations.json  (all files)
        data/graph/graph.json                   (node metadata)

Writes: data/graph/cycles_dataset.csv
        data/graph/cycles_dataset.json
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
GRAPH_DIR     = Path(__file__).parent.parent / "data" / "graph"

# ── Load node metadata ────────────────────────────────────────────────────────
with open(GRAPH_DIR / "graph.json", encoding="utf-8") as f:
    graph = json.load(f)

node_meta = {n["id"]: n for n in graph["nodes"]}

def law_name(law_id):
    return node_meta.get(law_id, {}).get("name", law_id)

def law_short(law_id):
    return node_meta.get(law_id, {}).get("short", "") or law_id[:20]

# ── Load all citations ────────────────────────────────────────────────────────
# edge_citations[(source, target)] = list of citation dicts
edge_citations = defaultdict(list)

citation_files = sorted(CITATIONS_DIR.glob("*_citations.json"))
print(f"Loading {len(citation_files)} citation files...")

for path in citation_files:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for c in data.get("citations", []):
        src = c.get("source_law", "")
        tgt = c.get("target_law_id", "")
        if src and tgt and tgt != "unresolved":
            edge_citations[(src, tgt)].append(c)

print(f"Loaded {sum(len(v) for v in edge_citations.values())} citations across "
      f"{len(edge_citations)} directed edges.")

# ── Find mutual pairs ─────────────────────────────────────────────────────────
seen = set()
pairs = []

for (src, tgt) in edge_citations:
    if (tgt, src) in edge_citations and (tgt, src) not in seen:
        seen.add((src, tgt))

        a_to_b = edge_citations[(src, tgt)]
        b_to_a = edge_citations[(tgt, src)]

        def best_citations(cits):
            """Return up to 3 best citations: prefer high confidence, dedupe text."""
            seen_text = set()
            result = []
            for conf in ("high", "medium", "low"):
                for c in cits:
                    if c.get("confidence") == conf:
                        txt = c.get("citation_text", "").strip()[:300]
                        if txt not in seen_text:
                            seen_text.add(txt)
                            result.append({
                                "article":       c.get("source_article", ""),
                                "target_article": c.get("target_article", ""),
                                "pattern":       c.get("pattern_name", ""),
                                "confidence":    c.get("confidence", ""),
                                "text":          txt,
                            })
                    if len(result) >= 3:
                        break
                if len(result) >= 3:
                    break
            return result

        pairs.append({
            "law_a":       src,
            "law_a_name":  law_name(src),
            "law_a_short": law_short(src),
            "law_b":       tgt,
            "law_b_name":  law_name(tgt),
            "law_b_short": law_short(tgt),
            "sector_a":    node_meta.get(src, {}).get("sector", "unknown"),
            "sector_b":    node_meta.get(tgt, {}).get("sector", "unknown"),
            "same_sector": node_meta.get(src, {}).get("sector") == node_meta.get(tgt, {}).get("sector"),
            "a_to_b_count": len(a_to_b),
            "b_to_a_count": len(b_to_a),
            "a_to_b_citations": best_citations(a_to_b),
            "b_to_a_citations": best_citations(b_to_a),
        })

pairs.sort(key=lambda p: (p["a_to_b_count"] + p["b_to_a_count"]), reverse=True)
print(f"Found {len(pairs)} mutual citation pairs.")

# ── Write JSON ────────────────────────────────────────────────────────────────
json_out = GRAPH_DIR / "cycles_dataset.json"
with open(json_out, "w", encoding="utf-8") as f:
    json.dump({
        "total_pairs": len(pairs),
        "note": "Cada par representa dos leyes que se citan mutuamente. "
                "Incluye hasta 3 citas textuales por dirección.",
        "pairs": pairs,
    }, f, ensure_ascii=False, indent=2)
print(f"Saved: {json_out}")

# ── Write CSV ─────────────────────────────────────────────────────────────────
csv_out = GRAPH_DIR / "cycles_dataset.csv"

def flatten_citations(cit_list):
    """Flatten up to 3 citations into pipe-separated string."""
    parts = []
    for c in cit_list:
        art = f"Art.{c['article']}" if c['article'] else "?"
        parts.append(f"[{art} · {c['confidence']} · {c['pattern']}] {c['text']}")
    return " ||| ".join(parts)

with open(csv_out, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow([
        "ley_a", "ley_a_nombre", "ley_a_corta",
        "ley_b", "ley_b_nombre", "ley_b_corta",
        "sector_a", "sector_b", "mismo_sector",
        "citas_a_a_b", "citas_b_a_a",
        "textos_a_cita_b", "textos_b_cita_a",
    ])
    for p in pairs:
        writer.writerow([
            p["law_a"], p["law_a_name"], p["law_a_short"],
            p["law_b"], p["law_b_name"], p["law_b_short"],
            p["sector_a"], p["sector_b"], p["same_sector"],
            p["a_to_b_count"], p["b_to_a_count"],
            flatten_citations(p["a_to_b_citations"]),
            flatten_citations(p["b_to_a_citations"]),
        ])

print(f"Saved: {csv_out}")
print(f"\nDone — {len(pairs)} pares de ciclos exportados.")
