"use strict";

const CONFIG = {
  articleGraphPath: "../data/graph/article_graph.json",
  maxHighlights: 6,
  highlightPalette: ["#ef476f", "#118ab2", "#06d6a0", "#f78c6b", "#7b61ff", "#ffbf69"],
  neutralNode: "#9db2c8",
  neutralLink: "rgba(142, 166, 192, 0.28)",
};

const state = {
  graph: null,
  fg: null,
  selectedNode: null,
  highlights: new Map(),
  showLinks: true,
  showArticleInTooltip: true,
};

const el = {
  nodes: document.getElementById("stat-nodes"),
  edges: document.getElementById("stat-edges"),
  laws: document.getElementById("stat-laws"),
  loading: document.getElementById("loading"),
  empty: document.getElementById("empty"),
  tooltip: document.getElementById("tooltip"),
  lawSelect: document.getElementById("law-select"),
  addHighlight: document.getElementById("add-highlight"),
  highlightList: document.getElementById("highlight-list"),
  resetCamera: document.getElementById("reset-camera"),
  focusSelection: document.getElementById("focus-selection"),
  toggleLinks: document.getElementById("toggle-links"),
  toggleArticles: document.getElementById("toggle-articles"),
  searchInput: document.getElementById("search-input"),
  searchResults: document.getElementById("search-results"),
  loadDemo: document.getElementById("load-demo"),
};

function getNodeColor(node) {
  return state.highlights.get(node.law_id)?.color || CONFIG.neutralNode;
}

function buildGraph(data) {
  state.graph = data;

  el.nodes.textContent = data.nodes.length.toLocaleString("es-MX");
  el.edges.textContent = data.links.length.toLocaleString("es-MX");
  el.laws.textContent = data.meta?.laws_count?.toLocaleString("es-MX") || "—";

  fillLawSelector(data.law_catalog || []);

  const fg = ForceGraph3D()(document.getElementById("graph-3d"))
    .graphData(data)
    .backgroundColor("#eef3fb")
    .nodeLabel(() => "")
    .nodeColor(getNodeColor)
    .nodeVal(n => Math.max(1.8, Math.min(8, (n.weight || 1) * 0.7)))
    .linkColor(() => state.showLinks ? CONFIG.neutralLink : "rgba(0,0,0,0)")
    .linkOpacity(0.23)
    .linkWidth(l => Math.min(1.8, 0.4 + (l.weight || 1) * 0.15))
    .onNodeHover(handleNodeHover)
    .onNodeClick(handleNodeClick)
    .onBackgroundClick(() => {
      state.selectedNode = null;
      refreshColors();
    })
    .d3Force("charge").strength(-45)
    .d3Force("link").distance(22)
    .cooldownTicks(150)
    .warmupTicks(35);

  fg.controls().enableDamping = true;
  fg.controls().dampingFactor = 0.08;

  state.fg = fg;
  refreshColors();
}

function handleNodeHover(node) {
  if (!node) {
    el.tooltip.classList.add("hidden");
    return;
  }

  const law = node.law_name || node.law_id || "Ley desconocida";
  const article = node.article || "?";
  const inDeg = node.in_degree ?? 0;
  const outDeg = node.out_degree ?? 0;
  el.tooltip.innerHTML = `
    <strong>${law}</strong><br/>
    ${state.showArticleInTooltip ? `Artículo: <b>${article}</b><br/>` : ""}
    Citado por: <b>${inDeg}</b> · Cita a: <b>${outDeg}</b>
  `;
  el.tooltip.classList.remove("hidden");

  window.onmousemove = (ev) => {
    el.tooltip.style.left = `${ev.clientX + 12}px`;
    el.tooltip.style.top = `${ev.clientY + 12}px`;
  };
}

function handleNodeClick(node) {
  state.selectedNode = node;
  if (!state.fg) return;
  const dist = 65;
  const ratio = 1 + dist / Math.hypot(node.x || 1, node.y || 1, node.z || 1);
  state.fg.cameraPosition(
    { x: (node.x || 0) * ratio, y: (node.y || 0) * ratio, z: (node.z || 0) * ratio },
    node,
    900
  );
  refreshColors();
}

function refreshColors() {
  if (!state.fg) return;
  const selectedId = state.selectedNode?.id;
  const neighbors = selectedId ? buildNeighborSet(selectedId) : null;

  state.fg
    .nodeColor((node) => {
      const base = getNodeColor(node);
      if (!neighbors) return base;
      return neighbors.has(node.id) ? base : "rgba(183, 197, 214, 0.24)";
    })
    .linkColor((link) => {
      if (!state.showLinks) return "rgba(0,0,0,0)";
      if (!neighbors) return CONFIG.neutralLink;
      const sid = typeof link.source === "object" ? link.source.id : link.source;
      const tid = typeof link.target === "object" ? link.target.id : link.target;
      return (sid === selectedId || tid === selectedId) ? "rgba(31,122,236,0.85)" : "rgba(190,205,224,0.08)";
    });
}

function buildNeighborSet(id) {
  const set = new Set([id]);
  for (const l of state.graph.links) {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    if (s === id) set.add(t);
    if (t === id) set.add(s);
  }
  return set;
}

function fillLawSelector(catalog) {
  const frag = document.createDocumentFragment();
  catalog.forEach((law) => {
    const opt = document.createElement("option");
    opt.value = law.id;
    opt.textContent = `${law.short || law.id} · ${law.name}`;
    frag.appendChild(opt);
  });
  el.lawSelect.appendChild(frag);
}

function addHighlightLaw() {
  const lawId = el.lawSelect.value;
  if (!lawId || state.highlights.has(lawId)) return;
  if (state.highlights.size >= CONFIG.maxHighlights) {
    alert(`Límite alcanzado (${CONFIG.maxHighlights} leyes resaltadas).`);
    return;
  }
  const color = CONFIG.highlightPalette[state.highlights.size % CONFIG.highlightPalette.length];
  const label = el.lawSelect.options[el.lawSelect.selectedIndex].textContent;
  state.highlights.set(lawId, { color, label });
  renderHighlightList();
  refreshColors();
}

function removeHighlightLaw(lawId) {
  state.highlights.delete(lawId);
  renderHighlightList();
  refreshColors();
}

function renderHighlightList() {
  el.highlightList.innerHTML = "";
  state.highlights.forEach((v, lawId) => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div class="highlight-item-left">
        <span class="swatch" style="background:${v.color}"></span>
        <span title="${v.label}">${v.label}</span>
      </div>
      <button data-id="${lawId}">Quitar</button>
    `;
    li.querySelector("button").addEventListener("click", () => removeHighlightLaw(lawId));
    el.highlightList.appendChild(li);
  });
}

function setupSearch() {
  el.searchInput.addEventListener("input", () => {
    const q = el.searchInput.value.trim().toLowerCase();
    el.searchResults.innerHTML = "";
    if (!q || !state.graph) {
      el.searchResults.classList.add("hidden");
      return;
    }
    const matches = state.graph.nodes
      .filter(n => (n.law_name || "").toLowerCase().includes(q) || (n.article || "").toLowerCase().includes(q) || n.id.toLowerCase().includes(q))
      .slice(0, 8);
    matches.forEach((n) => {
      const row = document.createElement("div");
      row.textContent = `${n.law_id}::${n.article} · ${(n.law_name || "").slice(0, 72)}`;
      row.addEventListener("click", () => {
        handleNodeClick(n);
        el.searchResults.classList.add("hidden");
        el.searchInput.value = `${n.law_id}::${n.article}`;
      });
      el.searchResults.appendChild(row);
    });
    el.searchResults.classList.toggle("hidden", matches.length === 0);
  });
}

async function loadRealData() {
  try {
    const res = await fetch(CONFIG.articleGraphPath);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data?.nodes?.length) throw new Error("empty graph");
    el.loading.classList.add("hidden");
    buildGraph(data);
  } catch {
    el.loading.classList.add("hidden");
    el.empty.classList.remove("hidden");
  }
}

function demoData() {
  const laws = [
    ["constitucion-politica", "Constitución", "CPEUM"],
    ["codigo-fiscal-federacion", "Código Fiscal de la Federación", "CFF"],
    ["ley-federal-del-trabajo", "Ley Federal del Trabajo", "LFT"],
    ["ley-del-seguro-social", "Ley del Seguro Social", "LSS"],
    ["ley-general-salud", "Ley General de Salud", "LGS"],
  ];
  const nodes = [];
  const links = [];
  laws.forEach(([id, name, short], li) => {
    for (let a = 1; a <= 22; a++) {
      nodes.push({
        id: `${id}::${a}`,
        law_id: id,
        law_name: name,
        law_short: short,
        article: String(a),
        weight: 1 + (a % 4),
        in_degree: 0,
        out_degree: 0,
      });
      if (a > 1) links.push({ source: `${id}::${a}`, target: `${id}::${a - 1}`, weight: 1 });
      if (li > 0 && a % 3 === 0) links.push({ source: `${id}::${a}`, target: `constitucion-politica::${(a % 15) + 1}`, weight: 2 });
    }
  });
  const degree = new Map();
  links.forEach(l => {
    const s = l.source; const t = l.target;
    degree.set(s, (degree.get(s) || { in: 0, out: 0 }));
    degree.set(t, (degree.get(t) || { in: 0, out: 0 }));
    degree.get(s).out += 1;
    degree.get(t).in += 1;
  });
  nodes.forEach(n => {
    const d = degree.get(n.id) || { in: 0, out: 0 };
    n.in_degree = d.in;
    n.out_degree = d.out;
  });
  return {
    nodes,
    links,
    law_catalog: laws.map(([id, name, short]) => ({ id, name, short })),
    meta: { laws_count: laws.length }
  };
}

function bindUI() {
  el.addHighlight.addEventListener("click", addHighlightLaw);
  el.resetCamera.addEventListener("click", () => {
    if (state.fg) state.fg.cameraPosition({ x: 0, y: 0, z: 180 }, { x: 0, y: 0, z: 0 }, 600);
  });
  el.focusSelection.addEventListener("click", () => {
    if (state.selectedNode) handleNodeClick(state.selectedNode);
  });
  el.toggleLinks.addEventListener("change", (e) => {
    state.showLinks = e.target.checked;
    refreshColors();
  });
  el.toggleArticles.addEventListener("change", (e) => {
    state.showArticleInTooltip = e.target.checked;
  });
  el.loadDemo.addEventListener("click", () => {
    el.empty.classList.add("hidden");
    buildGraph(demoData());
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  setupSearch();
  loadRealData();
});
