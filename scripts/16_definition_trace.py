#!/usr/bin/env python3
"""16_definition_trace.py

Builds definition trace outputs for legal concept dependency analysis.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEP_PATH = ROOT / "data" / "dependencies" / "dependencies.json"
OUT_PATH = ROOT / "data" / "dependencies" / "definition_trace_report.json"


def main() -> None:
    with open(DEP_PATH, encoding="utf-8") as f:
        deps = json.load(f).get("dependencies", [])

    traces = defaultdict(list)

    for d in deps:
        if d.get("dependency_type") != "definitional":
            continue

        target = d.get("target_law_id")
        if not target:
            continue

        traces[target].append({
            "source_law": d.get("source_law"),
            "source_article": d.get("source_article"),
            "target_article": d.get("target_article"),
            "dependency_subtype": d.get("dependency_subtype"),
            "confidence": d.get("confidence"),
            "reason": d.get("explanation"),
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "definition_dependency_targets": [
            {
                "law_id": law_id,
                "dependent_provisions": refs,
                "dependent_count": len(refs),
            }
            for law_id, refs in sorted(traces.items(), key=lambda x: len(x[1]), reverse=True)
        ],
        "notes": [
            "Este reporte identifica leyes que prestan definiciones a otras disposiciones.",
            "Útil para revisar consistencia conceptual antes de reformas o litigio estratégico.",
        ],
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved definition trace report to {OUT_PATH}")


if __name__ == "__main__":
    main()
