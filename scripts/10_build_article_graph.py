#!/usr/bin/env python3
"""
Build an optimized article-level graph JSON for the 3D dashboard.

Output:
  data/graph/article_graph.json
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.utils.dependency_taxonomy import classify_normative_instrument, normative_priority

CITATIONS_DIR = ROOT / "data" / "citations"
DEPENDENCIES_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
GRAPH_DIR = ROOT / "data" / "graph"
GRAPH_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = GRAPH_DIR / "article_graph.json"

MAX_NODES = 5000
MAX_EDGES = 20000


def _load_dependency_lookup():
  if not DEPENDENCIES_PATH.exists():
    return {}
  with open(DEPENDENCIES_PATH, "r", encoding="utf-8") as f:
    deps = json.load(f).get("dependencies", [])
  lookup = {}
  for d in deps:
    key = (
      d.get("source_law"),
      str(d.get("source_article") or "?"),
      d.get("target_law_id"),
      str(d.get("target_article") or "?"),
    )
    lookup[key] = d.get("dependency_type", "generic_unresolved")
  return lookup


def load_citations():
  dep_lookup = _load_dependency_lookup()
  for file in CITATIONS_DIR.glob("*_citations.json"):
    with open(file, "r", encoding="utf-8") as f:
      data = json.load(f)
    src_law = data.get("law_id") or file.stem.replace("_citations", "")
    for c in data.get("citations", []):
      tgt_law = c.get("target_law_id")
      if not tgt_law or tgt_law == "unresolved":
        continue
      src_art = str(c.get("source_article") or "?").strip() or "?"
      tgt_art = str(c.get("target_article") or "?").strip() or "?"
      yield {
        "source": f"{src_law}::{src_art}",
        "target": f"{tgt_law}::{tgt_art}",
        "source_law": src_law,
        "target_law": tgt_law,
        "dependency_type": dep_lookup.get((src_law, src_art, tgt_law, tgt_art), "generic_unresolved"),
      }


def main():
  edge_weights = Counter()
  in_degree = Counter()
  out_degree = Counter()
  law_names = {}
  edge_type_mix = defaultdict(Counter)

  for c in load_citations():
    if c["source"] == c["target"]:
      continue
    edge_weights[(c["source"], c["target"])] += 1
    edge_type_mix[(c["source"], c["target"])][c["dependency_type"]] += 1
    out_degree[c["source"]] += 1
    in_degree[c["target"]] += 1

    s_law = c["source_law"]
    t_law = c["target_law"]
    law_names.setdefault(s_law, s_law.replace("-", " ").title())
    law_names.setdefault(t_law, t_law.replace("-", " ").title())

  ranked_nodes = sorted(
    set([n for (s, t) in edge_weights.keys() for n in (s, t)]),
    key=lambda n: (in_degree[n] + out_degree[n]),
    reverse=True,
  )[:MAX_NODES]
  keep_nodes = set(ranked_nodes)

  links = []
  for (src, tgt), w in edge_weights.most_common(MAX_EDGES * 2):
    if src in keep_nodes and tgt in keep_nodes:
      links.append({"source": src, "target": tgt, "weight": w})
      links[-1]["dependency_type"] = edge_type_mix[(src, tgt)].most_common(1)[0][0]
    if len(links) >= MAX_EDGES:
      break

  nodes = []
  by_law_count = Counter()
  for nid in ranked_nodes:
    law_id, article = nid.split("::", 1)
    by_law_count[law_id] += 1
    nodes.append({
      "id": nid,
      "law_id": law_id,
      "law_name": law_names.get(law_id, law_id),
      "article": article,
      "in_degree": in_degree[nid],
      "out_degree": out_degree[nid],
      "weight": in_degree[nid] + out_degree[nid],
    })

  law_catalog = []
  for law_id, count in by_law_count.items():
    law_name = law_names.get(law_id, law_id)
    instrument_type = classify_normative_instrument(law_name)
    law_catalog.append({
      "id": law_id,
      "name": law_name,
      "short": law_id[:18],
      "instrument_type": instrument_type,
      "priority": normative_priority(instrument_type),
      "article_nodes": count,
    })

  # Put normas (constitucionales/reglamentarias/técnicas) on top of leyes in selector lists.
  law_catalog.sort(key=lambda x: (x["priority"], -x["article_nodes"], x["name"]))

  payload = {
    "nodes": nodes,
    "links": links,
    "law_catalog": law_catalog,
    "meta": {
      "laws_count": len(by_law_count),
      "nodes_count": len(nodes),
      "edges_count": len(links),
      "max_nodes": MAX_NODES,
      "max_edges": MAX_EDGES,
    },
  }

  with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)

  print(f"Saved {OUT_PATH} with {len(nodes)} nodes and {len(links)} edges.")


if __name__ == "__main__":
  main()
