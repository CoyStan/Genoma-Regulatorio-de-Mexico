"use strict";

const CONFIG = {
  articleGraphPaths: ["./data/graph/article_graph.json", "../data/graph/article_graph.json"],
  maxHighlights: 6,
  defaultVisibleNodes: 2500,
  highlightPalette: ["#ef476f", "#118ab2", "#06d6a0", "#f78c6b", "#7b61ff", "#ffbf69"],
  neutralNode: "#9db2c8",
  neutralLink: "rgba(142, 166, 192, 0.28)",
};

const state = {
  fullGraph: null,
  viewGraph: null,
  fg: null,
  selectedNode: null,
  highlights: new Map(),
  showLinks: true,
  showArticleInTooltip: true,
  maxNodes: CONFIG.defaultVisibleNodes,
  minEdgeWeight: 1,
  focusLaw: "",
};

const el = {
  nodes: document.getElementById("stat-nodes"),
  edges: document.getElementById("stat-edges"),
  laws: document.getElementById("stat-laws"),
  loading: document.getElementById("loading"),
  empty: document.getElementById("empty"),
  tooltip: document.getElementById("tooltip"),
  lawSelect: document.getElementById("law-select"),
  focusLawSelect: document.getElementById("focus-law-select"),
  addHighlight: document.getElementById("add-highlight"),
  highlightList: document.getElementById("highlight-list"),
  resetCamera: document.getElementById("reset-camera"),
  focusSelection: document.getElementById("focus-selection"),
  toggleLinks: document.getElementById("toggle-links"),
  toggleArticles: document.getElementById("toggle-articles"),
  searchInput: document.getElementById("search-input"),
  searchResults: document.getElementById("search-results"),
  loadDemo: document.getElementById("load-demo"),
  maxNodesRange: document.getElementById("max-nodes-range"),
  maxNodesLabel: document.getElementById("max-nodes-label"),
  edgeWeightRange: document.getElementById("edge-weight-range"),
  edgeWeightLabel: document.getElementById("edge-weight-label"),
  applyPerformance: document.getElementById("apply-performance"),
};

function getNodeColor(node) {
  return state.highlights.get(node.law_id)?.color || CONFIG.neutralNode;
}

function computeViewGraph() {
  const full = state.fullGraph;
  if (!full) return null;

  let nodes = full.nodes;
  if (state.focusLaw) {
    nodes = nodes.filter(n => n.law_id === state.focusLaw);
  }

  nodes = [...nodes]
    .sort((a, b) => (b.weight || 0) - (a.weight || 0))
    .slice(0, state.maxNodes);

  const keep = new Set(nodes.map(n => n.id));

  const links = full.links.filter(l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return keep.has(s) && keep.has(t) && (l.weight || 1) >= state.minEdgeWeight;
  });

  // keep orphan nodes out for cleaner view
  const connected = new Set();
  links.forEach(l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    connected.add(s); connected.add(t);
  });

  const filteredNodes = nodes.filter(n => connected.has(n.id));
  const laws = new Set(filteredNodes.map(n => n.law_id));

  return { nodes: filteredNodes, links, meta: { laws_count: laws.size } };
}

function renderGraph(data) {
  state.viewGraph = data;

  el.nodes.textContent = data.nodes.length.toLocaleString("es-MX");
  el.edges.textContent = data.links.length.toLocaleString("es-MX");
  el.laws.textContent = data.meta?.laws_count?.toLocaleString("es-MX") || "—";

  if (!state.fg) {
    state.fg = ForceGraph3D()(document.getElementById("graph-3d"))
      .backgroundColor("#eef3fb")
      .nodeLabel(() => "")
      .nodeVal(n => Math.max(1.8, Math.min(8, (n.weight || 1) * 0.7)))
      .linkOpacity(0.22)
      .linkWidth(l => Math.min(1.8, 0.4 + (l.weight || 1) * 0.15))
      .onNodeHover(handleNodeHover)
      .onNodeClick(handleNodeClick)
      .onBackgroundClick(() => {
        state.selectedNode = null;
        refreshColors();
      })
      .d3Force("charge").strength(-42)
      .d3Force("link").distance(20)
      .cooldownTicks(120)
      .warmupTicks(30);

    state.fg.controls().enableDamping = true;
    state.fg.controls().dampingFactor = 0.08;
  }

  state.fg.graphData(data);
  refreshColors();
}

function rebuildAndRender() {
  const view = computeViewGraph();
  if (view) renderGraph(view);
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
  if (!state.fg || !state.viewGraph) return;
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
  for (const l of state.viewGraph.links) {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    if (s === id) set.add(t);
    if (t === id) set.add(s);
  }
  return set;
}

function fillLawSelector(catalog) {
  const fragA = document.createDocumentFragment();
  const fragB = document.createDocumentFragment();
  catalog.forEach((law) => {
    const text = `${law.short || law.id} · ${law.name}`;
    const optA = document.createElement("option");
    optA.value = law.id;
    optA.textContent = text;
    fragA.appendChild(optA);

    const optB = document.createElement("option");
    optB.value = law.id;
    optB.textContent = text;
    fragB.appendChild(optB);
  });
  el.lawSelect.appendChild(fragA);
  el.focusLawSelect.appendChild(fragB);
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
    if (!q || !state.viewGraph) {
      el.searchResults.classList.add("hidden");
      return;
    }
    const matches = state.viewGraph.nodes
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
    let data = null;
    for (const path of CONFIG.articleGraphPaths) {
      const res = await fetch(path);
      if (res.ok) {
        const payload = await res.json();
        if (payload?.nodes?.length) {
          data = payload;
          break;
        }
      }
    }
    if (!data) throw new Error("empty graph");
    state.fullGraph = data;
    fillLawSelector(data.law_catalog || []);
    el.loading.classList.add("hidden");
    rebuildAndRender();
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
    for (let a = 1; a <= 120; a++) {
      nodes.push({ id: `${id}::${a}`, law_id: id, law_name: name, law_short: short, article: String(a), weight: 1 + (a % 5) });
      if (a > 1) links.push({ source: `${id}::${a}`, target: `${id}::${a - 1}`, weight: 1 });
      if (li > 0 && a % 5 === 0) links.push({ source: `${id}::${a}`, target: `constitucion-politica::${(a % 60) + 1}`, weight: 2 });
    }
  });
  return {
    nodes,
    links,
    law_catalog: laws.map(([id, name, short]) => ({ id, name, short })),
    meta: { laws_count: laws.length },
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

  el.maxNodesRange.addEventListener("input", (e) => {
    state.maxNodes = Number(e.target.value);
    el.maxNodesLabel.textContent = String(state.maxNodes);
  });
  el.edgeWeightRange.addEventListener("input", (e) => {
    state.minEdgeWeight = Number(e.target.value);
    el.edgeWeightLabel.textContent = String(state.minEdgeWeight);
  });
  el.focusLawSelect.addEventListener("change", (e) => {
    state.focusLaw = e.target.value;
  });
  el.applyPerformance.addEventListener("click", rebuildAndRender);

  el.loadDemo.addEventListener("click", () => {
    el.empty.classList.add("hidden");
    state.fullGraph = demoData();
    fillLawSelector(state.fullGraph.law_catalog || []);
    rebuildAndRender();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindUI();
  setupSearch();
  loadRealData();
});
