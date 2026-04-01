#!/usr/bin/env python3
"""
12_generate_charts.py — Generate Twitter-ready charts for the Genoma Regulatorio thread.

Writes: docs/assets/charts/chart_{1..5}.png
"""

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

GRAPH_DIR  = Path(__file__).parent.parent / "data" / "graph"
DEFS_DIR   = Path(__file__).parent.parent / "data" / "definitions"
OUT_DIR    = Path(__file__).parent.parent / "docs" / "assets" / "charts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Shared style ──────────────────────────────────────────────────────────────
BG      = "#0f172a"
FG      = "#f1f5f9"
ACCENT  = "#38bdf8"
MUTED   = "#64748b"
GRID    = "#1e293b"

SECTOR_COLORS = {
    "constitucional":       "#E63946",
    "penal":                "#F4A261",
    "fiscal":               "#2A9D8F",
    "financiero":           "#457B9D",
    "administrativo":       "#6A4C93",
    "trabajo":              "#F77F00",
    "salud":                "#E9C46A",
    "ambiental":            "#52B788",
    "educacion":            "#90BE6D",
    "energia":              "#FF6B6B",
    "seguridad":            "#4D908E",
    "militar":              "#577590",
    "agrario":              "#A8C5DA",
    "mercantil":            "#C77DFF",
    "electoral":            "#F9C74F",
    "anticorrupcion":       "#43AA8B",
    "migracion":            "#B5838D",
    "social":               "#F28482",
    "propiedad-intelectual":"#84A98C",
    "telecomunicaciones":   "#6D6875",
    "competencia":          "#B7B7A4",
    "civil":                "#A2D2FF",
    "unknown":              "#64748b",
}

def style_ax(ax, title, subtitle=None):
    ax.set_facecolor(BG)
    ax.tick_params(colors=FG, labelsize=11)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)
    ax.set_title(title, color=FG, fontsize=15, fontweight="bold", pad=14)
    if subtitle:
        ax.annotate(subtitle, xy=(0.5, 1.005), xycoords="axes fraction",
                    ha="center", va="bottom", color=MUTED, fontsize=10)

def save(fig, name, subtitle_line=None):
    fig.patch.set_facecolor(BG)
    # Watermark
    fig.text(0.98, 0.01, "github.com/CoyStan/Genoma-Regulatorio-de-Mexico",
             ha="right", va="bottom", color=MUTED, fontsize=8)
    if subtitle_line:
        fig.text(0.5, 0.97, subtitle_line, ha="center", va="top",
                 color=MUTED, fontsize=10)
    path = OUT_DIR / name
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"Saved: {path}")


# ── Load data ─────────────────────────────────────────────────────────────────
with open(GRAPH_DIR / "graph.json", encoding="utf-8") as f:
    graph = json.load(f)
with open(GRAPH_DIR / "simplification.json", encoding="utf-8") as f:
    simp = json.load(f)
with open(GRAPH_DIR / "diagnostics.json", encoding="utf-8") as f:
    diag = json.load(f)
with open(DEFS_DIR / "_all_definitions.json", encoding="utf-8") as f:
    defs = json.load(f)

nodes = {n["id"]: n for n in graph["nodes"] if not n.get("stub")}


# ── Chart 1: Top 10 leyes más citadas ─────────────────────────────────────────
def chart1():
    top = sorted(nodes.values(), key=lambda n: n.get("in_degree", 0), reverse=True)[:10]
    top = list(reversed(top))  # bottom-up for horizontal bar

    names  = [n.get("short") or n["id"][:20] for n in top]
    values = [n.get("in_degree", 0) for n in top]
    colors = [SECTOR_COLORS.get(n.get("sector", "unknown"), "#64748b") for n in top]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names, values, color=colors, height=0.65, zorder=3)
    ax.bar_label(bars, fmt="%d", color=FG, padding=4, fontsize=11)
    ax.set_xlim(0, max(values) * 1.15)
    ax.set_xlabel("Leyes que la citan", color=FG, fontsize=11)
    ax.grid(axis="x", color=GRID, zorder=0)
    style_ax(ax, "Las 10 leyes más influyentes del sistema jurídico mexicano")
    fig.tight_layout()
    save(fig, "chart_1_top10_leyes.png")

chart1()


# ── Chart 2: Comunidades regulatorias ────────────────────────────────────────
def chart2():
    communities = diag.get("communities", {})
    # Aggregate by community label
    from collections import Counter, defaultdict
    comm_counts = Counter()
    comm_sector = defaultdict(Counter)
    for law_id, info in communities.items():
        label = info.get("label", "Otro")
        comm_counts[label] += 1
        sector = nodes.get(law_id, {}).get("sector", "unknown")
        comm_sector[label][sector] += 1

    labels = [k for k, _ in comm_counts.most_common()]
    counts = [comm_counts[k] for k in labels]

    # Pick dominant sector color per community
    def dom_color(label):
        top_sector = comm_sector[label].most_common(1)
        if top_sector:
            return SECTOR_COLORS.get(top_sector[0][0], "#64748b")
        return "#64748b"

    colors = [dom_color(l) for l in labels]

    fig, ax = plt.subplots(figsize=(9, 9))
    wedges, texts, autotexts = ax.pie(
        counts, labels=None, colors=colors,
        autopct="%1.0f%%", startangle=140,
        pctdistance=0.75, wedgeprops=dict(width=0.55, edgecolor=BG, linewidth=2),
        textprops=dict(color=FG),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_color(BG)
        at.set_fontweight("bold")

    legend_patches = [mpatches.Patch(color=colors[i], label=f"{labels[i]} ({counts[i]})")
                      for i in range(len(labels))]
    ax.legend(handles=legend_patches, loc="lower center", bbox_to_anchor=(0.5, -0.08),
              ncol=2, frameon=False, labelcolor=FG, fontsize=11)

    style_ax(ax, "7 comunidades regulatorias en el sistema jurídico federal")
    save(fig, "chart_2_comunidades.png")

chart2()


# ── Chart 3: Scatter — abrogación segura ──────────────────────────────────────
def chart3():
    removal = simp["removal_candidates"]

    x = [r["in_degree"] for r in removal]
    y = [r["cascade_score"] for r in removal]
    score = [r["removal_safety_score"] for r in removal]

    # Color by safety score
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=0, vmax=100)

    fig, ax = plt.subplots(figsize=(10, 7))
    sc = ax.scatter(x, y, c=score, cmap=cmap, norm=norm,
                    s=55, alpha=0.82, edgecolors="none", zorder=3)

    # Annotate extreme safe candidates
    safe = sorted(removal, key=lambda r: r["removal_safety_score"], reverse=True)[:6]
    for r in safe:
        label = r.get("short") or r["name"][:18]
        ax.annotate(label, (r["in_degree"], r["cascade_score"]),
                    textcoords="offset points", xytext=(5, 3),
                    color=FG, fontsize=8.5, alpha=0.9)

    cb = fig.colorbar(sc, ax=ax, pad=0.01)
    cb.set_label("Score de seguridad (100 = eliminar sin riesgo)", color=FG, fontsize=10)
    cb.ax.yaxis.set_tick_params(color=FG)
    plt.setp(cb.ax.yaxis.get_ticklabels(), color=FG)

    ax.set_xlabel("Leyes que la citan (in-degree)", color=FG, fontsize=11)
    ax.set_ylabel("Impacto en cascada", color=FG, fontsize=11)
    ax.grid(color=GRID, zorder=0)
    style_ax(ax, "¿Qué leyes se pueden eliminar sin romper el sistema?")
    fig.tight_layout()
    save(fig, "chart_3_abrogacion.png",
         subtitle_line="Verde = seguro abrogar · Rojo = crítica para el sistema")

chart3()


# ── Chart 4: Conflictos de definición ────────────────────────────────────────
def chart4():
    conflicts = defs.get("top_conflicts", [])[:12]
    conflicts = list(reversed(conflicts))

    terms  = [f'"{c["term"]}"' for c in conflicts]
    counts = [c["num_laws"] for c in conflicts]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(terms, counts, color=ACCENT, height=0.6, zorder=3)
    ax.bar_label(bars, fmt="%d leyes", color=FG, padding=4, fontsize=11)
    ax.set_xlim(0, max(counts) * 1.2)
    ax.set_xlabel("Número de leyes con definición distinta", color=FG, fontsize=11)
    ax.grid(axis="x", color=GRID, zorder=0)
    style_ax(ax, 'La misma palabra, definida diferente en múltiples leyes')
    fig.tight_layout()
    save(fig, "chart_4_conflictos_definicion.png",
         subtitle_line="Fuente de ambigüedad jurídica sistémica")

chart4()


# ── Chart 5: Candidatos a fusión (top 10 pares) ──────────────────────────────
def chart5():
    mergers = simp["merger_candidates"][:10]
    mergers = list(reversed(mergers))

    labels = [f'{m["short_a"] or m["name_a"][:14]}  ↔  {m["short_b"] or m["name_b"][:14]}'
              for m in mergers]
    scores = [m["merger_score"] for m in mergers]
    colors = [SECTOR_COLORS.get(m.get("sector", "unknown"), "#64748b") for m in mergers]

    fig, ax = plt.subplots(figsize=(11, 6))
    bars = ax.barh(labels, scores, color=colors, height=0.62, zorder=3)
    ax.bar_label(bars, fmt="%.0f", color=FG, padding=4, fontsize=11)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Score de fusión (100 = fusión ideal)", color=FG, fontsize=11)
    ax.grid(axis="x", color=GRID, zorder=0)
    style_ax(ax, "Leyes que podrían fusionarse en un solo instrumento")
    fig.tight_layout()
    save(fig, "chart_5_fusion.png",
         subtitle_line="Se citan mutuamente · mismo sector · baja dependencia externa")

chart5()

print("\nTodos los gráficos generados en docs/assets/charts/")
