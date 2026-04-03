#!/usr/bin/env python3
"""15_reform_impact_report.py

Produces a lawyer-facing reform impact report from typed dependencies.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEP_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
OUT_PATH = ROOT / "data" / "dependencies" / "reform_impact_report.json"


def main() -> None:
    with open(DEP_PATH, encoding="utf-8") as f:
        deps = json.load(f).get("dependencies", [])

    inbound = Counter()
    outbound = Counter()
    type_mix = defaultdict(Counter)
    article_touchpoints = defaultdict(set)

    for d in deps:
        src = d.get("source_law")
        tgt = d.get("target_law_id")
        dtype = d.get("dependency_type", "generic_unresolved")
        if not src or not tgt:
            continue

        outbound[src] += 1
        inbound[tgt] += 1
        type_mix[tgt][dtype] += 1
        if d.get("source_article"):
            article_touchpoints[tgt].add(str(d["source_article"]))

    top_impact_targets = []
    for law_id, in_count in inbound.most_common(200):
        out_count = outbound.get(law_id, 0)
        spillover_score = in_count * 2 + out_count
        top_impact_targets.append({
            "law_id": law_id,
            "inbound_dependencies": in_count,
            "outbound_dependencies": out_count,
            "spillover_score": spillover_score,
            "article_touchpoints_count": len(article_touchpoints.get(law_id, set())),
            "dependency_type_mix": dict(type_mix.get(law_id, {})),
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "graph-neighborhood-over-typed-dependencies-v1",
        "top_reform_impact_laws": top_impact_targets[:100],
        "notes": [
            "Score alto sugiere que una reforma puede irradiar efectos a múltiples leyes y artículos.",
            "No reemplaza análisis doctrinal, jurisprudencial o de técnica legislativa.",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Saved reform impact report to {OUT_PATH}")


if __name__ == "__main__":
    main()
