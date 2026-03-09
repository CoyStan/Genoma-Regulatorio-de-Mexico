/**
 * graph.js — D3.js force-directed citation network for Genoma Regulatorio de México
 *
 * Loads data/graph/graph.json and renders an interactive force-directed graph.
 * Falls back to demo data if the real graph file is not available.
 */

"use strict";

// ============================================================
// Configuration
// ============================================================

const CONFIG = {
  graphDataPath: "../data/graph/graph.json",
  diagnosticsPath: "../data/graph/diagnostics.json",
  simulation: {
    chargeStrength: -200,
    linkDistance: 60,
    linkStrength: 0.3,
    collideRadius: 12,
    alphaDecay: 0.02,
  },
  node: {
    minRadius: 4,
    maxRadius: 28,
    defaultColor: "#4ecdc4",
  },
  colors: {
    // Color palette for community detection (Louvain)
    community: [
      "#e63946", "#457b9d", "#2a9d8f", "#e9c46a",
      "#f4a261", "#264653", "#a8dadc", "#6d6875",
      "#b5838d", "#e76f51", "#52b788", "#9b5de5",
    ],
    // Color scale for sectors
    sector: {
      "fiscal":              "#e9c46a",
      "trabajo":             "#2a9d8f",
      "constitucional":      "#e63946",
      "penal":               "#6d6875",
      "civil":               "#457b9d",
      "financiero":          "#f4a261",
      "administrativo":      "#52b788",
      "ambiental":           "#57cc99",
      "salud":               "#80b918",
      "educacion":           "#9b5de5",
      "transparencia":       "#4cc9f0",
      "electoral":           "#ff6b6b",
      "comercio":            "#f9844a",
      "seguridad":           "#b5838d",
      "energia":             "#f8961e",
      "migracion":           "#90be6d",
      "anticorrupcion":      "#c9184a",
      "telecomunicaciones":  "#3a0ca3",
      "propiedad-intelectual":"#7b2d8b",
      "seguridad-social":    "#4895ef",
      "default":             "#546e7a",
    },
  },
};

// ============================================================
// Demo data (used when real graph.json is not yet generated)
// ============================================================

const DEMO_DATA = generateDemoData();

function generateDemoData() {
  const sectors = ["fiscal", "trabajo", "penal", "civil", "financiero", "administrativo", "ambiental", "salud"];
  const laws = [
    { id: "constitucion-politica", name: "Constitución Política de los Estados Unidos Mexicanos", short: "CPEUM", sector: "constitucional" },
    { id: "codigo-fiscal-federacion", name: "Código Fiscal de la Federación", short: "CFF", sector: "fiscal" },
    { id: "ley-isr", name: "Ley del Impuesto sobre la Renta", short: "LISR", sector: "fiscal" },
    { id: "ley-iva", name: "Ley del Impuesto al Valor Agregado", short: "LIVA", sector: "fiscal" },
    { id: "ley-federal-del-trabajo", name: "Ley Federal del Trabajo", short: "LFT", sector: "trabajo" },
    { id: "ley-del-seguro-social", name: "Ley del Seguro Social", short: "LSS", sector: "seguridad-social" },
    { id: "codigo-penal-federal", name: "Código Penal Federal", short: "CPF", sector: "penal" },
    { id: "codigo-civil-federal", name: "Código Civil Federal", short: "CCF", sector: "civil" },
    { id: "ley-instituciones-credito", name: "Ley de Instituciones de Crédito", short: "LIC", sector: "financiero" },
    { id: "loapf", name: "Ley Orgánica de la Administración Pública Federal", short: "LOAPF", sector: "administrativo" },
    { id: "lgeepa", name: "Ley General del Equilibrio Ecológico", short: "LGEEPA", sector: "ambiental" },
    { id: "ley-general-salud", name: "Ley General de Salud", short: "LGS", sector: "salud" },
    { id: "ley-amparo", name: "Ley de Amparo", short: "LA", sector: "judicial" },
    { id: "lgtaip", name: "Ley General de Transparencia", short: "LGTAIP", sector: "transparencia" },
    { id: "ley-banco-mexico", name: "Ley del Banco de México", short: "LBM", sector: "financiero" },
    { id: "ley-aduanera", name: "Ley Aduanera", short: "LA", sector: "comercio-exterior" },
    { id: "ley-general-educacion", name: "Ley General de Educación", short: "LGE", sector: "educacion" },
    { id: "lgipe", name: "Ley General de Instituciones y Procedimientos Electorales", short: "LGIPE", sector: "electoral" },
    { id: "lftr", name: "Ley Federal de Telecomunicaciones y Radiodifusión", short: "LFTR", sector: "telecomunicaciones" },
    { id: "ley-industria-electrica", name: "Ley de la Industria Eléctrica", short: "LIE", sector: "energia" },
  ];

  // Assign metrics
  laws.forEach((law, i) => {
    law.in_degree = Math.floor(Math.random() * 15) + (i < 5 ? 10 : 0);
    law.out_degree = Math.floor(Math.random() * 12) + 1;
    law.pagerank = Math.random() * 0.1 + (i < 5 ? 0.08 : 0.01);
    law.betweenness = Math.random() * 0.1;
    law.community = Math.floor(i / 4);
    law.cascade_score = Math.floor(Math.random() * 50) + (i < 5 ? 20 : 0);
    law.url = `https://www.diputados.gob.mx/LeyesBiblio/`;
  });

  // Create citation edges
  const links = [
    { source: "ley-isr", target: "codigo-fiscal-federacion", citation_count: 45, confidence: "high" },
    { source: "ley-iva", target: "codigo-fiscal-federacion", citation_count: 38, confidence: "high" },
    { source: "ley-del-seguro-social", target: "ley-federal-del-trabajo", citation_count: 22, confidence: "high" },
    { source: "codigo-penal-federal", target: "constitucion-politica", citation_count: 18, confidence: "high" },
    { source: "ley-instituciones-credito", target: "ley-banco-mexico", citation_count: 15, confidence: "high" },
    { source: "ley-isr", target: "constitucion-politica", citation_count: 12, confidence: "high" },
    { source: "ley-federal-del-trabajo", target: "constitucion-politica", citation_count: 25, confidence: "high" },
    { source: "loapf", target: "constitucion-politica", citation_count: 30, confidence: "high" },
    { source: "ley-amparo", target: "constitucion-politica", citation_count: 40, confidence: "high" },
    { source: "lgeepa", target: "constitucion-politica", citation_count: 8, confidence: "high" },
    { source: "ley-general-salud", target: "constitucion-politica", citation_count: 10, confidence: "high" },
    { source: "lgtaip", target: "constitucion-politica", citation_count: 14, confidence: "high" },
    { source: "lgipe", target: "constitucion-politica", citation_count: 20, confidence: "high" },
    { source: "ley-aduanera", target: "codigo-fiscal-federacion", citation_count: 16, confidence: "high" },
    { source: "ley-aduanera", target: "constitucion-politica", citation_count: 5, confidence: "medium" },
    { source: "ley-general-educacion", target: "constitucion-politica", citation_count: 12, confidence: "high" },
    { source: "ley-industria-electrica", target: "constitucion-politica", citation_count: 9, confidence: "high" },
    { source: "lftr", target: "constitucion-politica", citation_count: 11, confidence: "high" },
    { source: "ley-banco-mexico", target: "constitucion-politica", citation_count: 7, confidence: "high" },
    { source: "codigo-civil-federal", target: "constitucion-politica", citation_count: 6, confidence: "medium" },
    { source: "ley-instituciones-credito", target: "codigo-fiscal-federacion", citation_count: 8, confidence: "medium" },
    { source: "ley-instituciones-credito", target: "constitucion-politica", citation_count: 10, confidence: "high" },
  ];

  return { nodes: laws, links };
}

// ============================================================
// State
// ============================================================

let graphData = null;
let simulation = null;
let selectedNode = null;
let colorMode = "community";
let sizeMetric = "pagerank";
let showLabels = true;
let filterIsolated = false;
let activeFilter = "";
let svg, g, nodeGroup, linkGroup, labelGroup;
let width, height;

// D3 selections
let linkSel, nodeSel, labelSel;

// ============================================================
// Color helpers
// ============================================================

function getNodeColor(d) {
  if (colorMode === "community") {
    const palette = CONFIG.colors.community;
    return palette[(d.community || 0) % palette.length];
  }
  if (colorMode === "sector") {
    return CONFIG.colors.sector[d.sector] || CONFIG.colors.sector.default;
  }
  if (colorMode === "pagerank") {
    const scale = d3.scaleSequential(d3.interpolateYlOrRd)
      .domain([0, graphData ? d3.max(graphData.nodes, n => n.pagerank) : 0.1]);
    return scale(d.pagerank || 0);
  }
  return CONFIG.node.defaultColor;
}

function getNodeRadius(d) {
  if (!graphData) return 6;
  const vals = graphData.nodes.map(n => n[sizeMetric] || 0);
  const maxVal = d3.max(vals) || 1;
  const minR = CONFIG.node.minRadius;
  const maxR = CONFIG.node.maxRadius;
  const v = d[sizeMetric] || 0;
  return minR + (v / maxVal) * (maxR - minR);
}

// ============================================================
// Graph initialization
// ============================================================

function initSVG() {
  const container = document.getElementById("graph-container");
  width = container.clientWidth;
  height = container.clientHeight;

  svg = d3.select("#graph-svg")
    .attr("width", width)
    .attr("height", height);

  g = d3.select("#graph-root");
  linkGroup = d3.select("#links-layer");
  nodeGroup = d3.select("#nodes-layer");
  labelGroup = d3.select("#labels-layer");

  // Zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.05, 5])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
    });

  svg.call(zoom);

  // Store zoom ref
  svg._zoom = zoom;

  // Reset zoom button
  document.getElementById("btn-reset-zoom").addEventListener("click", () => {
    svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
  });

  // Fit all button
  document.getElementById("btn-fit").addEventListener("click", fitGraph);

  // Handle resize
  window.addEventListener("resize", () => {
    width = container.clientWidth;
    height = container.clientHeight;
    svg.attr("width", width).attr("height", height);
    if (simulation) {
      simulation.force("center", d3.forceCenter(width / 2, height / 2));
      simulation.alpha(0.1).restart();
    }
  });
}

function fitGraph() {
  if (!nodeGroup) return;
  const bounds = g.node().getBBox();
  if (!bounds.width || !bounds.height) return;

  const padding = 40;
  const scale = Math.min(
    (width - padding * 2) / bounds.width,
    (height - padding * 2) / bounds.height,
    2
  );
  const tx = width / 2 - scale * (bounds.x + bounds.width / 2);
  const ty = height / 2 - scale * (bounds.y + bounds.height / 2);

  svg.transition().duration(600)
    .call(svg._zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}

function renderGraph(data) {
  graphData = data;

  // Update header stats
  document.getElementById("stat-nodes").textContent = data.nodes.length.toLocaleString("es-MX");
  document.getElementById("stat-edges").textContent = data.links.length.toLocaleString("es-MX");
  const numCommunities = new Set(data.nodes.map(n => n.community)).size;
  document.getElementById("stat-communities").textContent = numCommunities;

  // Build sector filter
  const sectors = [...new Set(data.nodes.map(n => n.sector).filter(Boolean))].sort();
  const sectorSelect = document.getElementById("sector-filter");
  sectors.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s.charAt(0).toUpperCase() + s.slice(1).replace(/-/g, " ");
    sectorSelect.appendChild(opt);
  });

  // Build neighbor lookup
  const neighborMap = new Map();
  data.nodes.forEach(n => neighborMap.set(n.id, new Set()));
  data.links.forEach(l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    if (neighborMap.has(s)) neighborMap.get(s).add(t);
    if (neighborMap.has(t)) neighborMap.get(t).add(s);
  });
  graphData._neighborMap = neighborMap;

  // Build incoming/outgoing lookup for detail panel
  const inMap = new Map();
  const outMap = new Map();
  data.nodes.forEach(n => { inMap.set(n.id, []); outMap.set(n.id, []); });
  data.links.forEach(l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    if (outMap.has(s)) outMap.get(s).push(t);
    if (inMap.has(t)) inMap.get(t).push(s);
  });
  graphData._inMap = inMap;
  graphData._outMap = outMap;

  drawSimulation(data);
}

function drawSimulation(data) {
  // Clear previous
  linkGroup.selectAll("*").remove();
  nodeGroup.selectAll("*").remove();
  labelGroup.selectAll("*").remove();

  // Filter if needed
  let nodes = data.nodes.slice();
  let links = data.links.slice();

  if (filterIsolated) {
    const connected = new Set();
    links.forEach(l => {
      connected.add(typeof l.source === "object" ? l.source.id : l.source);
      connected.add(typeof l.target === "object" ? l.target.id : l.target);
    });
    nodes = nodes.filter(n => connected.has(n.id));
  }

  if (activeFilter) {
    nodes = nodes.filter(n => n.sector === activeFilter);
    const nodeIds = new Set(nodes.map(n => n.id));
    links = links.filter(l => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      return nodeIds.has(s) && nodeIds.has(t);
    });
  }

  // Build D3 simulation
  simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id)
      .distance(CONFIG.simulation.linkDistance)
      .strength(CONFIG.simulation.linkStrength))
    .force("charge", d3.forceManyBody().strength(d => {
      const r = getNodeRadius(d);
      return CONFIG.simulation.chargeStrength * (r / CONFIG.node.minRadius);
    }))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(d => getNodeRadius(d) + 4).iterations(2))
    .alphaDecay(CONFIG.simulation.alphaDecay);

  // Draw links
  linkSel = linkGroup.selectAll(".link")
    .data(links)
    .join("line")
    .attr("class", "link")
    .attr("marker-end", "url(#arrow)")
    .attr("stroke-width", d => Math.min(3, 0.5 + (d.citation_count || 1) / 15));

  // Draw nodes
  nodeSel = nodeGroup.selectAll(".node")
    .data(nodes, d => d.id)
    .join("g")
    .attr("class", "node")
    .call(d3.drag()
      .on("start", dragStarted)
      .on("drag", dragged)
      .on("end", dragEnded))
    .on("click", (event, d) => {
      event.stopPropagation();
      selectNode(d);
    })
    .on("mouseenter", (event, d) => showTooltip(event, d))
    .on("mousemove", (event) => moveTooltip(event))
    .on("mouseleave", hideTooltip);

  nodeSel.append("circle")
    .attr("r", d => getNodeRadius(d))
    .attr("fill", d => getNodeColor(d))
    .attr("stroke", d => d3.color(getNodeColor(d)).darker(0.5))
    .attr("stroke-width", 1.5);

  // Draw labels
  labelSel = labelGroup.selectAll(".node-label")
    .data(nodes.filter(d => getNodeRadius(d) > 8), d => d.id)
    .join("text")
    .attr("class", d => `node-label${showLabels ? "" : " hidden-label"}`)
    .text(d => d.short || d.name.substring(0, 12));

  // Click on background to deselect
  svg.on("click", () => {
    if (selectedNode) {
      selectedNode = null;
      resetHighlight();
      closeDetailPanel();
    }
  });

  // Simulation tick
  simulation.on("tick", () => {
    linkSel
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => clampedTarget(d).x)
      .attr("y2", d => clampedTarget(d).y);

    nodeSel.attr("transform", d => `translate(${d.x},${d.y})`);

    labelSel
      .attr("x", d => d.x)
      .attr("y", d => d.y + getNodeRadius(d) + 10);
  });

  // After graph settles, fit it
  simulation.on("end", () => {
    setTimeout(fitGraph, 100);
  });
}

// Pull arrow endpoint back to node edge
function clampedTarget(d) {
  const r = getNodeRadius(d.target) + 6;
  const dx = d.target.x - d.source.x;
  const dy = d.target.y - d.source.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  return {
    x: d.target.x - (dx / dist) * r,
    y: d.target.y - (dy / dist) * r,
  };
}

// ============================================================
// Drag
// ============================================================

function dragStarted(event, d) {
  if (!event.active) simulation.alphaTarget(0.2).restart();
  d.fx = d.x;
  d.fy = d.y;
}

function dragged(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

function dragEnded(event, d) {
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null;
  d.fy = null;
}

// ============================================================
// Node selection and highlighting
// ============================================================

function selectNode(d) {
  selectedNode = d;
  highlightNeighborhood(d);
  showDetailPanel(d);
}

function highlightNeighborhood(d) {
  const neighbors = graphData._neighborMap.get(d.id) || new Set();

  nodeSel.classed("faded", n => n.id !== d.id && !neighbors.has(n.id));
  nodeSel.classed("selected", n => n.id === d.id);

  linkSel.classed("highlighted", l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return s === d.id || t === d.id;
  });
  linkSel.classed("faded", l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return s !== d.id && t !== d.id;
  });
}

function resetHighlight() {
  nodeSel.classed("faded selected", false);
  linkSel.classed("highlighted faded", false);
}

// ============================================================
// Detail panel
// ============================================================

function showDetailPanel(d) {
  const panel = document.getElementById("detail-panel");
  panel.classList.remove("hidden");

  document.getElementById("detail-short").textContent = d.short || "";
  document.getElementById("detail-name").textContent = d.name;
  document.getElementById("detail-sector").textContent = d.sector || "";

  document.getElementById("d-pagerank").textContent = d.pagerank ? d.pagerank.toFixed(4) : "—";
  document.getElementById("d-indegree").textContent = d.in_degree ?? "—";
  document.getElementById("d-outdegree").textContent = d.out_degree ?? "—";
  document.getElementById("d-cascade").textContent = d.cascade_score ?? "—";

  // Populate source/target lists
  const nodeById = new Map(graphData.nodes.map(n => [n.id, n]));
  const sources = (graphData._inMap.get(d.id) || []).slice(0, 20);
  const targets = (graphData._outMap.get(d.id) || []).slice(0, 20);

  renderLawList("detail-sources", sources, nodeById);
  renderLawList("detail-targets", targets, nodeById);

  // URL
  const urlEl = document.getElementById("detail-url");
  if (d.url) {
    urlEl.href = d.url;
    urlEl.style.display = "inline-block";
  } else {
    urlEl.style.display = "none";
  }
}

function renderLawList(listId, ids, nodeById) {
  const ul = document.getElementById(listId);
  ul.innerHTML = "";
  if (!ids.length) {
    ul.innerHTML = '<li style="color:var(--text-muted);font-size:11px">Ninguna</li>';
    return;
  }
  ids.forEach(id => {
    const n = nodeById.get(id);
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="law-short">${(n && n.short) || ""}</span>
      <span>${(n && n.name) || id}</span>
    `;
    li.addEventListener("click", () => {
      if (n) {
        const nodeData = graphData.nodes.find(nd => nd.id === n.id);
        if (nodeData) selectNode(nodeData);
      }
    });
    ul.appendChild(li);
  });
}

function closeDetailPanel() {
  document.getElementById("detail-panel").classList.add("hidden");
}

document.getElementById("close-panel").addEventListener("click", () => {
  closeDetailPanel();
  resetHighlight();
  selectedNode = null;
});

// ============================================================
// Tooltip
// ============================================================

function showTooltip(event, d) {
  const tt = document.getElementById("tooltip");
  tt.classList.remove("hidden");
  tt.innerHTML = `
    <div class="tt-name">${d.short ? `<strong>${d.short}</strong> — ` : ""}${d.name}</div>
    <div class="tt-row">Sector: <span>${d.sector || "—"}</span></div>
    <div class="tt-row">Citada por: <span>${d.in_degree ?? 0}</span> leyes</div>
    <div class="tt-row">Cita a: <span>${d.out_degree ?? 0}</span> leyes</div>
    <div class="tt-row">PageRank: <span>${d.pagerank ? d.pagerank.toFixed(4) : "—"}</span></div>
    <div class="tt-row">Impacto cascada: <span>${d.cascade_score ?? "—"}</span></div>
  `;
  moveTooltip(event);
}

function moveTooltip(event) {
  const tt = document.getElementById("tooltip");
  const margin = 16;
  let x = event.clientX + margin;
  let y = event.clientY + margin;
  if (x + 280 > window.innerWidth) x = event.clientX - 280 - margin;
  if (y + 150 > window.innerHeight) y = event.clientY - 150 - margin;
  tt.style.left = `${x}px`;
  tt.style.top = `${y}px`;
}

function hideTooltip() {
  document.getElementById("tooltip").classList.add("hidden");
}

// ============================================================
// Controls
// ============================================================

// Search
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");

searchInput.addEventListener("input", () => {
  const q = searchInput.value.trim().toLowerCase();
  searchResults.innerHTML = "";

  if (!q || !graphData) {
    searchResults.classList.add("hidden");
    return;
  }

  const matches = graphData.nodes
    .filter(n =>
      n.name.toLowerCase().includes(q) ||
      (n.short && n.short.toLowerCase().includes(q)) ||
      n.id.includes(q)
    )
    .slice(0, 8);

  if (!matches.length) {
    searchResults.classList.add("hidden");
    return;
  }

  matches.forEach(n => {
    const item = document.createElement("div");
    item.className = "dropdown-item";
    item.innerHTML = `<span class="item-short">${n.short || ""}</span>${n.name}`;
    item.addEventListener("click", () => {
      searchInput.value = n.name;
      searchResults.classList.add("hidden");
      focusNode(n);
    });
    searchResults.appendChild(item);
  });

  searchResults.classList.remove("hidden");
});

document.addEventListener("click", (e) => {
  if (!searchInput.contains(e.target)) {
    searchResults.classList.add("hidden");
  }
});

function focusNode(d) {
  selectNode(d);

  // Pan to node
  if (d.x != null && d.y != null) {
    const transform = d3.zoomTransform(svg.node());
    const newX = width / 2 - transform.k * d.x;
    const newY = height / 2 - transform.k * d.y;
    svg.transition().duration(600)
      .call(svg._zoom.transform, d3.zoomIdentity.translate(newX, newY).scale(transform.k));
  }
}

// Sector filter
document.getElementById("sector-filter").addEventListener("change", (e) => {
  activeFilter = e.target.value;
  if (graphData) drawSimulation(graphData);
});

// Metric select
document.getElementById("metric-select").addEventListener("change", (e) => {
  sizeMetric = e.target.value;
  if (nodeSel) {
    nodeSel.select("circle")
      .transition().duration(300)
      .attr("r", d => getNodeRadius(d));
  }
});

// Color mode
document.getElementById("color-select").addEventListener("change", (e) => {
  colorMode = e.target.value;
  if (nodeSel) {
    nodeSel.select("circle")
      .transition().duration(300)
      .attr("fill", d => getNodeColor(d))
      .attr("stroke", d => d3.color(getNodeColor(d)).darker(0.5));
  }
});

// Show labels toggle
document.getElementById("show-labels").addEventListener("change", (e) => {
  showLabels = e.target.checked;
  if (labelSel) {
    labelSel.classed("hidden-label", !showLabels);
  }
});

// Filter isolated
document.getElementById("filter-isolated").addEventListener("change", (e) => {
  filterIsolated = e.target.checked;
  if (graphData) drawSimulation(graphData);
});

// ============================================================
// Diagnostics panel
// ============================================================

document.getElementById("diagnostics-toggle").addEventListener("click", () => {
  const panel = document.getElementById("diagnostics-panel");
  panel.classList.toggle("hidden");
  if (!panel.classList.contains("hidden")) {
    loadDiagnostics();
  }
});

document.getElementById("close-diagnostics").addEventListener("click", () => {
  document.getElementById("diagnostics-panel").classList.add("hidden");
});

async function loadDiagnostics() {
  const content = document.getElementById("diagnostics-content");

  try {
    const res = await fetch(CONFIG.diagnosticsPath);
    if (!res.ok) throw new Error("not found");
    const data = await res.json();
    renderDiagnostics(data);
  } catch {
    content.innerHTML = `
      <p class="loading-text">
        Los diagnósticos no están disponibles aún.<br/>
        Ejecuta <code>python scripts/07_diagnostics.py</code>
      </p>`;
  }
}

function renderDiagnostics(data) {
  const content = document.getElementById("diagnostics-content");
  const esc = s => String(s).replace(/</g, "&lt;");

  const sections = [];

  // Hub laws
  if (data.hub_laws && data.hub_laws.length) {
    const items = data.hub_laws.slice(0, 8).map(h =>
      `<li><strong>${esc(h.short || h.law_id)}</strong> — ${esc(h.name.substring(0, 45))}
       <span class="diag-badge badge-high">PR: ${h.pagerank.toFixed(3)}</span></li>`
    ).join("");
    sections.push(`
      <div class="diag-section">
        <h4>Leyes más centrales <span class="diag-count">${data.hub_laws.length}</span></h4>
        <ul class="diag-list">${items}</ul>
      </div>`);
  }

  // Orphan references
  if (data.orphan_references && data.orphan_references.length) {
    const items = data.orphan_references.slice(0, 6).map(o =>
      `<li><strong>${esc(o.source_name.substring(0, 35))}</strong> →
       <code>${esc(o.target_law_id)}</code>
       <span class="diag-badge badge-med">${esc(o.type)}</span></li>`
    ).join("");
    sections.push(`
      <div class="diag-section">
        <h4>Referencias huérfanas <span class="diag-count">${data.orphan_references.length}</span></h4>
        <ul class="diag-list">${items}</ul>
      </div>`);
  }

  // Circular dependencies
  if (data.circular_dependencies && data.circular_dependencies.length) {
    const items = data.circular_dependencies.slice(0, 6).map(c =>
      `<li>${c.law_ids.join(" → ")} <span class="diag-badge badge-low">ciclo ${c.length}</span></li>`
    ).join("");
    sections.push(`
      <div class="diag-section">
        <h4>Dependencias circulares <span class="diag-count">${data.circular_dependencies.length}</span></h4>
        <ul class="diag-list">${items}</ul>
      </div>`);
  }

  // Definition conflicts
  if (data.definition_conflicts && data.definition_conflicts.length) {
    const items = data.definition_conflicts.slice(0, 6).map(c =>
      `<li><strong>"${esc(c.term)}"</strong> — definida en ${c.num_laws} leyes</li>`
    ).join("");
    sections.push(`
      <div class="diag-section">
        <h4>Conflictos de definición <span class="diag-count">${data.definition_conflicts.length}</span></h4>
        <ul class="diag-list">${items}</ul>
      </div>`);
  }

  content.innerHTML = sections.join("") || '<p class="loading-text">No hay datos de diagnóstico.</p>';
}

// ============================================================
// Data loading
// ============================================================

async function loadGraphData() {
  try {
    const res = await fetch(CONFIG.graphDataPath);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (!data.nodes || !data.nodes.length) throw new Error("empty graph");

    hideOverlay();
    renderGraph(data);
  } catch (err) {
    console.warn("Could not load graph.json:", err.message);
    showEmptyState();
  }
}

function hideOverlay() {
  document.getElementById("loading-overlay").style.display = "none";
  document.getElementById("empty-state").classList.add("hidden");
}

function showEmptyState() {
  document.getElementById("loading-overlay").style.display = "none";
  document.getElementById("empty-state").classList.remove("hidden");
}

document.getElementById("btn-load-demo").addEventListener("click", () => {
  document.getElementById("empty-state").classList.add("hidden");
  renderGraph(DEMO_DATA);
});

// ============================================================
// Bootstrap
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  initSVG();
  loadGraphData();
});
