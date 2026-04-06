#!/usr/bin/env python3
"""17_harmonization_report.py

Identifies legal harmonization and coordinated-review candidates.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEP_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
OUT_PATH = ROOT / "data" / "dependencies" / "harmonization_report.json"


def main() -> None:
    with open(DEP_PATH, encoding="utf-8") as f:
        deps = json.load(f).get("dependencies", [])

    pair_counter = Counter()
    pair_types = defaultdict(Counter)

    for d in deps:
        src = d.get("source_law")
        tgt = d.get("target_law_id")
        if not src or not tgt or src == tgt:
            continue
        pair = tuple(sorted([src, tgt]))
        pair_counter[pair] += 1
        pair_types[pair][d.get("dependency_type", "generic_unresolved")] += 1

    candidates = []
    for pair, count in pair_counter.most_common(250):
        if count < 2:
            continue
        diversity = len(pair_types[pair])
        priority = count + (diversity * 1.5)
        candidates.append({
            "law_pair": list(pair),
            "cross_reference_count": count,
            "dependency_type_diversity": diversity,
            "type_breakdown": dict(pair_types[pair]),
            "review_priority_score": round(priority, 2),
            "review_rationale": "Alta interacción y diversidad de tipos de dependencia; revisar armónicamente.",
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harmonization_candidates": candidates[:100],
        "notes": [
            "Lista orientada a revisión jurídica coordinada entre estatutos y reglamentos.",
            "Puntaje no equivale a invalidez normativa; es una señal de coordinación potencial.",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved harmonization report to {OUT_PATH}")


if __name__ == "__main__":
    main()
