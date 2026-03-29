# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Genoma Regulatorio de México** is a 7-stage ETL pipeline that downloads all ~296 Mexican federal laws from diputados.gob.mx, extracts cross-citation relationships between them, and produces an interactive D3.js network visualization with NetworkX-computed metrics.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_patterns.py -v

# Run full pipeline (sequential, each stage depends on prior outputs)
python scripts/01_scrape.py
python scripts/02_parse.py
python scripts/03_extract_citations.py
python scripts/04_resolve_entities.py
python scripts/05_extract_definitions.py   # optional
python scripts/06_build_graph.py
python scripts/07_diagnostics.py

# Serve frontend locally
cd frontend && python -m http.server 8080
```

## Architecture

### Pipeline Data Flow

Each stage reads from and writes to the `data/` directory. Stages are idempotent (SHA-256 dedup, JSON status tracking):

```
diputados.gob.mx
    → 01_scrape.py       → data/raw/<law_id>.{doc,json}
    → 02_parse.py        → data/processed/<law_id>.json        (articles + metadata)
    → 03_extract_citations.py → data/citations/<law_id>_citations.json  (raw citations)
    → 04_resolve_entities.py  → data/citations/ (updated)      (raw names → canonical IDs)
    → 05_extract_definitions.py → data/definitions/            (optional term index)
    → 06_build_graph.py  → data/graph/graph.{graphml,json}, metrics.json
    → 07_diagnostics.py  → data/graph/diagnostics.{json,md}
```

### Core Modules (`scripts/utils/`)

- **`patterns.py`** — 19 regex patterns (14 primary, 5 secondary) for citation extraction. `PRIMARY_PATTERNS` target formulaic legal phrases ("conforme a lo dispuesto en", "en términos de", etc.) with high confidence; `SECONDARY_PATTERNS` cast wider nets at medium confidence.

- **`lookup.py`** — Registry of 296 canonical federal laws (`CANONICAL_LAWS` dict) and reverse alias lookup (`ALIASES` dict). `resolve_law_name()` tries: exact match → acronym match → fuzzy match (SequenceMatcher ≥ 0.75 threshold) → partial match (first 15 chars). Unresolved citations logged to `data/lookup/unresolved.json`.

- **`metrics.py`** — Wraps NetworkX to compute PageRank, betweenness centrality, HITS (hub/authority), Louvain community detection, and cascade scoring. `graph_to_json_format()` converts to D3.js-compatible format.

### Key Configuration (inline in scripts, no `.env`)

| Script | Key Setting | Default |
|--------|-------------|---------|
| `01_scrape.py` | `REQUEST_DELAY_SECONDS` | 1.5s (polite scraping) |
| `03_extract_citations.py` | `CONTEXT_CHARS` | 150 chars around matches |
| `04_resolve_entities.py` | `FUZZY_THRESHOLD` | 0.75 |
| `06_build_graph.py` | `MIN_CONFIDENCE_FOR_EDGE` | "medium" |

### Citation Data Model

```json
{
  "source_law": "ley-federal-del-trabajo",
  "source_article": "123",
  "target_law_raw": "Ley del Seguro Social",
  "target_law_id": "ley-del-seguro-social",
  "confidence": "high",
  "pattern_name": "conforme_dispuesto",
  "citation_text": "...conforme a lo dispuesto en la Ley..."
}
```

All edges carry confidence levels (`high`/`medium`/`low`/`unresolved`), used in Stage 6 to filter the graph.

### Frontend

`frontend/` is a standalone static site. `graph.js` loads `data/graph/graph.json` (produced by Stage 6) and renders a D3.js v7 force-directed graph. It has a demo mode ("Cargar demostración") with 20 sample laws when no data directory is available.

## Testing

Tests cover the two most logic-dense modules:
- `tests/test_patterns.py` — ~35 real legal text samples validating citation regex
- `tests/test_resolution.py` — entity resolution across exact/acronym/alias/fuzzy/partial strategies

When adding citation patterns, add corresponding test cases in `test_patterns.py` with real-world legal text.
