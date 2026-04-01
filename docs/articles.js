/**
 * articles.js — Articles tab logic for Genoma Regulatorio de México.
 * Loads article_stats.json and renders top-cited articles + per-law drilldown.
 */

(function () {
  "use strict";

  const STATS_PATH = "data/graph/article_stats.json";

  const SECTOR_COLORS = {
    constitucional: "#E63946", penal: "#F4A261", fiscal: "#2A9D8F",
    financiero: "#457B9D", administrativo: "#6A4C93", trabajo: "#F77F00",
    salud: "#E9C46A", ambiental: "#52B788", educacion: "#90BE6D",
    energia: "#FF6B6B", seguridad: "#4D908E", militar: "#577590",
    agrario: "#A8C5DA", mercantil: "#C77DFF", electoral: "#F9C74F",
    anticorrupcion: "#43AA8B", migracion: "#B5838D", social: "#F28482",
    "propiedad-intelectual": "#84A98C", telecomunicaciones: "#6D6875",
    competencia: "#B7B7A4", civil: "#A2D2FF", unknown: "#64748b",
  };

  let statsData = null;
  let allLaws = [];   // [{id, name, short, sector, pagerank}, ...]

  // -------------------------------------------------------------------------
  // Tab switching
  // -------------------------------------------------------------------------
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const target = btn.dataset.tab;
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      // Show/hide header and controls for graph tab
      const isGraph = target === "graph-tab";
      document.getElementById("app-header").style.display = isGraph ? "" : "none";
      document.getElementById("controls").style.display   = isGraph ? "" : "none";
      document.getElementById("graph-container").style.display = isGraph ? "" : "none";

      // Show articles tab
      const artTab = document.getElementById("articles-tab");
      if (artTab) artTab.classList.toggle("active", !isGraph);

      if (!isGraph && !statsData) loadStats();
    });
  });

  // Make graph tab content show by default (articles tab hidden)
  const artTab = document.getElementById("articles-tab");
  if (artTab) artTab.classList.remove("active");

  // -------------------------------------------------------------------------
  // Load data
  // -------------------------------------------------------------------------
  async function loadStats() {
    try {
      const res = await fetch(STATS_PATH);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      statsData = await res.json();

      allLaws = Object.entries(statsData.by_law).map(([id, d]) => ({
        id, name: d.name, short: d.short, sector: d.sector, pagerank: d.pagerank,
      })).sort((a, b) => (b.pagerank || 0) - (a.pagerank || 0));

      renderLawList(allLaws);
      renderTopTable(statsData.top_cited_articles);
    } catch (e) {
      document.getElementById("art-main").innerHTML =
        `<p style="color:#f87171;padding:20px">Error cargando datos: ${e.message}</p>`;
    }
  }

  // -------------------------------------------------------------------------
  // Sidebar law list
  // -------------------------------------------------------------------------
  function renderLawList(laws) {
    const container = document.getElementById("art-law-list");
    container.innerHTML = laws.map(l => `
      <div class="art-law-item" data-id="${l.id}">
        <div class="law-short" style="color:${SECTOR_COLORS[l.sector] || '#60a5fa'}">${l.short || l.id.slice(0,12)}</div>
        <div class="law-name-small">${l.name.slice(0, 45)}</div>
      </div>
    `).join("");

    container.querySelectorAll(".art-law-item").forEach(el => {
      el.addEventListener("click", () => {
        container.querySelectorAll(".art-law-item").forEach(e => e.classList.remove("selected"));
        el.classList.add("selected");
        showDrilldown(el.dataset.id);
      });
    });
  }

  document.getElementById("art-law-search").addEventListener("input", function () {
    const q = this.value.toLowerCase();
    if (!allLaws.length) return;
    const filtered = q
      ? allLaws.filter(l => l.name.toLowerCase().includes(q) || (l.short || "").toLowerCase().includes(q))
      : allLaws;
    renderLawList(filtered);
  });

  // -------------------------------------------------------------------------
  // Top-cited articles table
  // -------------------------------------------------------------------------
  function renderTopTable(articles) {
    const maxIn = articles[0]?.in_degree || 1;
    const tbody = document.querySelector("#art-top-table tbody");
    tbody.innerHTML = articles.map((a, i) => {
      const color = SECTOR_COLORS[a.sector] || "#64748b";
      const pct = Math.round((a.in_degree / maxIn) * 100);
      return `
        <tr>
          <td style="color:#64748b">${i + 1}</td>
          <td><span style="color:${color};font-weight:700">${a.law_short}</span></td>
          <td class="art-num">Art. ${a.article}</td>
          <td><span class="sector-badge" style="background:${color}22;color:${color}">${a.sector}</span></td>
          <td style="color:#f1c40f;font-weight:600">${a.in_degree.toLocaleString()}</td>
          <td class="bar-cell"><div class="bar-bg"><div class="bar-fill" style="width:${pct}%"></div></div></td>
        </tr>`;
    }).join("");

    // Click row → drilldown to that law
    tbody.querySelectorAll("tr").forEach((row, i) => {
      row.style.cursor = "pointer";
      row.addEventListener("click", () => {
        const lawId = articles[i].law_id;
        // highlight in sidebar
        const sidebar = document.getElementById("art-law-list");
        sidebar.querySelectorAll(".art-law-item").forEach(el => {
          el.classList.toggle("selected", el.dataset.id === lawId);
        });
        showDrilldown(lawId);
      });
    });
  }

  // -------------------------------------------------------------------------
  // Law drilldown
  // -------------------------------------------------------------------------
  function showDrilldown(lawId) {
    const law = statsData.by_law[lawId];
    if (!law) return;

    document.getElementById("art-top-section").classList.add("hidden");
    const dd = document.getElementById("art-drilldown");
    dd.classList.add("visible");

    document.getElementById("art-drilldown-title").textContent =
      `${law.short || lawId} — ${law.name}`;
    document.getElementById("art-drilldown-sub").textContent =
      `${law.articles.length} artículos con actividad de citación · Sector: ${law.sector}`;

    const color = SECTOR_COLORS[law.sector] || "#60a5fa";
    document.getElementById("art-drilldown-title").style.color = color;

    const container = document.getElementById("art-cards-container");

    if (!law.articles.length) {
      container.innerHTML = `<p style="color:#64748b">Sin datos de artículos para esta ley.</p>`;
      return;
    }

    container.innerHTML = law.articles.map(art => {
      const citesHTML = art.cites.length
        ? art.cites.map(t => `<span class="ref-pill" title="${t.law_id}">${t.short} ×${t.count}</span>`).join("")
        : `<span style="color:#334155">—</span>`;
      const citedHTML = art.cited_by.length
        ? art.cited_by.map(s => `<span class="ref-pill" title="${s.law_id}">${s.short} ×${s.count}</span>`).join("")
        : `<span style="color:#334155">—</span>`;

      const artLabel = art.article === "?" ? "General" : `Artículo ${art.article}`;

      return `
        <div class="art-card">
          <div class="art-card-header">
            <span class="art-card-num">${artLabel}</span>
            <div class="art-card-badges">
              ${art.in_degree  ? `<span class="badge-in">← ${art.in_degree} citas recibidas</span>` : ""}
              ${art.out_degree ? `<span class="badge-out">→ ${art.out_degree} citas emitidas</span>` : ""}
            </div>
          </div>
          <div class="art-card-refs">
            ${art.out_degree ? `<div class="art-ref-group"><strong>Cita a:</strong> ${citesHTML}</div>` : ""}
            ${art.in_degree  ? `<div class="art-ref-group"><strong>Citado por:</strong> ${citedHTML}</div>` : ""}
          </div>
        </div>`;
    }).join("");
  }

  document.getElementById("art-back").addEventListener("click", () => {
    document.getElementById("art-top-section").classList.remove("hidden");
    document.getElementById("art-drilldown").classList.remove("visible");
    document.getElementById("art-law-list")
      .querySelectorAll(".art-law-item").forEach(e => e.classList.remove("selected"));
  });

})();
