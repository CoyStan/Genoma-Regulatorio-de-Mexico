#!/usr/bin/env python3
"""20_build_corpus_layers.py

Builds a corpus-layer registry to support legal dependency intelligence workflows.
Layer 1: normative core (Constitución, leyes/códigos, reglamentos)
Layer 2: change layer (decretos, acuerdos, transitorios)
Layer 3: interpretive-prepared (fallback placeholder)
"""

from __future__ import annotations

import sys
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils.dependency_taxonomy import infer_corpus_layer

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_PATH = ROOT / "data" / "graph" / "corpus_layers.json"


def main() -> None:
    records = []
    counts = Counter()

    for path in sorted(PROCESSED_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            law = json.load(f)

        layer = infer_corpus_layer(law)
        counts[layer] += 1
        records.append({
            "law_id": law.get("id", path.stem),
            "name": law.get("name", ""),
            "short_name": law.get("short_name", ""),
            "layer": layer,
            "is_reglamento": "reglamento" in (law.get("name", "").lower()),
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "layers_summary": dict(counts),
        "records": records,
        "notes": [
            "Este archivo soporta segmentación del corpus para workflows de abogados.",
            "La clasificación de capa es heurística y puede revisarse por dominio/práctica.",
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Saved corpus layer registry to {OUT_PATH}")


if __name__ == "__main__":
    main()
