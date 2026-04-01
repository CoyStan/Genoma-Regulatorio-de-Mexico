#!/usr/bin/env python3
"""
09_article_stats.py — Build article-level stats JSON for the dashboard tab.

Writes: docs/data/graph/article_stats.json
"""

import json
from collections import defaultdict, Counter
from pathlib import Path

CITATIONS_DIR = Path(__file__).parent.parent / "data" / "citations"
GRAPH_JSON    = Path(__file__).parent.parent / "data" / "graph" / "graph.json"
OUT_PATH      = Path(__file__).parent.parent / "docs" / "data" / "graph" / "article_stats.json"

TOP_LAWS_FOR_DRILLDOWN = 60   # Include per-article breakdown for this many laws
TOP_CITED_ARTICLES     = 100  # Top cited specific articles (excluding art.?)

def main():
    with open(GRAPH_JSON) as f:
        nodes = json.load(f)["nodes"]
    law_meta = {n["id"]: n for n in nodes}

    # -----------------------------------------------------------------------
    # Pass 1: collect all citations
    # -----------------------------------------------------------------------
    # article_in[(law, art)]  = list of (src_law, src_art)
    # article_out[(law, art)] = list of (tgt_law, tgt_art)
    article_in  = defaultdict(list)
    article_out = defaultdict(list)

    for path in sorted(CITATIONS_DIR.glob("*_citations.json")):
        with open(path) as f:
            data = json.load(f)
        src_law = data.get("law_id", path.stem)
        for c in data.get("citations", []):
            tgt_law = c.get("target_law_id")
            if not tgt_law or tgt_law == "unresolved":
                continue
            src_art = str(c.get("source_article") or "?")
            tgt_art = str(c.get("target_article") or "?")
            article_out[(src_law, src_art)].append((tgt_law, tgt_art))
            article_in[(tgt_law, tgt_art)].append((src_law, src_art))

    # -----------------------------------------------------------------------
    # Top cited specific articles (exclude art.? — those are law-level)
    # -----------------------------------------------------------------------
    specific = {k: v for k, v in article_in.items() if k[1] != "?"}
    top_specific = sorted(specific.items(), key=lambda x: len(x[1]), reverse=True)[:TOP_CITED_ARTICLES]

    top_cited_articles = []
    for (law, art), sources in top_specific:
        meta = law_meta.get(law, {})
        citing_laws = Counter(s[0] for s in sources)
        top_cited_articles.append({
            "law_id":    law,
            "law_name":  meta.get("name", law),
            "law_short": meta.get("short", law[:12]),
            "sector":    meta.get("sector", "unknown"),
            "article":   art,
            "in_degree": len(sources),
            "out_degree": len(article_out.get((law, art), [])),
            "top_citing_laws": [
                {"law_id": l, "short": law_meta.get(l, {}).get("short", l[:12]), "count": n}
                for l, n in citing_laws.most_common(8)
            ],
        })

    # -----------------------------------------------------------------------
    # Per-law article breakdown for top N laws by total citation activity
    # -----------------------------------------------------------------------
    law_activity = Counter()
    for (law, art), sources in article_in.items():
        law_activity[law] += len(sources)
    for (law, art), targets in article_out.items():
        law_activity[law] += len(targets)

    top_law_ids = [law for law, _ in law_activity.most_common(TOP_LAWS_FOR_DRILLDOWN)]

    by_law = {}
    for law_id in top_law_ids:
        meta = law_meta.get(law_id, {})

        # Gather all articles that appear for this law
        arts = set()
        for (l, a) in article_out:
            if l == law_id:
                arts.add(a)
        for (l, a) in article_in:
            if l == law_id:
                arts.add(a)

        articles = []
        for art in sorted(arts, key=lambda x: (x == "?", int(x) if x.isdigit() else 0, x)):
            out_targets = article_out.get((law_id, art), [])
            in_sources  = article_in.get((law_id, art), [])

            # Aggregate targets by target law
            tgt_by_law = Counter(t[0] for t in out_targets)
            src_by_law = Counter(s[0] for s in in_sources)

            articles.append({
                "article":   art,
                "out_degree": len(out_targets),
                "in_degree":  len(in_sources),
                "cites": [
                    {"law_id": l, "short": law_meta.get(l, {}).get("short", l[:12]),
                     "sector": law_meta.get(l, {}).get("sector", "unknown"), "count": n}
                    for l, n in tgt_by_law.most_common(10)
                ],
                "cited_by": [
                    {"law_id": l, "short": law_meta.get(l, {}).get("short", l[:12]),
                     "sector": law_meta.get(l, {}).get("sector", "unknown"), "count": n}
                    for l, n in src_by_law.most_common(10)
                ],
            })

        # Sort articles by total degree desc (most active first)
        articles.sort(key=lambda x: x["in_degree"] + x["out_degree"], reverse=True)

        by_law[law_id] = {
            "name":     meta.get("name", law_id),
            "short":    meta.get("short", law_id[:12]),
            "sector":   meta.get("sector", "unknown"),
            "pagerank": meta.get("pagerank", 0),
            "articles": articles[:80],  # cap per law to keep file size sane
        }

    result = {
        "top_cited_articles": top_cited_articles,
        "by_law": by_law,
        "meta": {
            "total_article_nodes": len(set(list(article_in.keys()) + list(article_out.keys()))),
            "total_citation_edges": sum(len(v) for v in article_out.values()),
            "laws_with_drilldown": len(by_law),
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, separators=(",", ":"))

    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"Written: {OUT_PATH}  ({size_kb} KB)")
    print(f"  Top cited articles: {len(top_cited_articles)}")
    print(f"  Laws with drilldown: {len(by_law)}")
    print(f"  Total article nodes: {result['meta']['total_article_nodes']}")

if __name__ == "__main__":
    main()
