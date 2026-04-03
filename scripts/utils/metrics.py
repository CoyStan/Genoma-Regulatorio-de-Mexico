"""
Network metrics computation for the citation graph.
Uses NetworkX. All functions take a DiGraph and return dicts keyed by node ID.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import networkx as nx


def compute_degree_metrics(G: nx.DiGraph) -> dict[str, dict]:
    """Compute in-degree, out-degree, and total degree for each node."""
    metrics: dict[str, dict] = {}
    for node in G.nodes():
        metrics[node] = {
            "in_degree": G.in_degree(node),
            "out_degree": G.out_degree(node),
            "total_degree": G.in_degree(node) + G.out_degree(node),
        }
    return metrics


def compute_pagerank(G: nx.DiGraph, alpha: float = 0.85) -> dict[str, float]:
    """
    Compute PageRank for all nodes.
    Higher PageRank = more structurally important law (frequently cited by important laws).
    """
    try:
        return nx.pagerank(G, alpha=alpha, max_iter=1000)
    except nx.PowerIterationFailedConvergence:
        return nx.pagerank(G, alpha=alpha, max_iter=5000, tol=1e-4)


def compute_betweenness_centrality(G: nx.DiGraph, normalized: bool = True) -> dict[str, float]:
    """
    Compute betweenness centrality.
    High betweenness = law sits on many shortest paths between other laws.
    Acts as a "bridge" or bottleneck in the regulatory network.
    """
    return nx.betweenness_centrality(G, normalized=normalized, weight=None, k=min(100, len(G)))


def compute_hits(G: nx.DiGraph) -> tuple[dict[str, float], dict[str, float]]:
    """
    Compute HITS algorithm (hubs and authorities).
    Hub = law that cites many important laws.
    Authority = law that is cited by many important laws.
    Returns (hubs, authorities).
    """
    try:
        hubs, authorities = nx.hits(G, max_iter=1000)
        return hubs, authorities
    except nx.PowerIterationFailedConvergence:
        # Fall back to uniform if HITS doesn't converge
        n = G.number_of_nodes()
        uniform = {node: 1.0 / n for node in G.nodes()}
        return uniform, uniform


def compute_community_louvain(G: nx.DiGraph) -> dict[str, int]:
    """
    Detect communities using the Louvain method on the undirected version.
    Returns node → community_id mapping.
    """
    try:
        from community import best_partition  # python-louvain
        undirected = G.to_undirected()
        return best_partition(undirected)
    except ImportError:
        # Fallback: greedy modularity on undirected graph
        undirected = G.to_undirected()
        communities = nx.community.greedy_modularity_communities(undirected)
        mapping: dict[str, int] = {}
        for i, community in enumerate(communities):
            for node in community:
                mapping[node] = i
        return mapping


def compute_clustering_coefficient(G: nx.DiGraph) -> dict[str, float]:
    """Compute local clustering coefficient for each node (on undirected version)."""
    undirected = G.to_undirected()
    return nx.clustering(undirected)


def find_strongly_connected_components(G: nx.DiGraph) -> list[set]:
    """Find all strongly connected components (circular dependency clusters)."""
    sccs = list(nx.strongly_connected_components(G))
    # Sort by size descending
    return sorted(sccs, key=len, reverse=True)


CPEUM_ID = "constitucion-politica-de-los-estados-unidos-mexicanos"

def find_circular_dependencies(G: nx.DiGraph) -> list[list[str]]:
    """
    Find mutual citations (length-2 cycles) efficiently in O(E).
    Two laws that cite each other are a circular dependency.

    The Constitution (CPEUM) is excluded: cycles involving it reflect
    constitutional hierarchy and implementation authority, not peer-to-peer
    circular dependence between laws of the same rank.
    """
    cycles = []
    edges = set(G.edges())
    seen = set()
    for u, v in edges:
        if u == CPEUM_ID or v == CPEUM_ID:
            continue
        if (v, u) in edges and (v, u) not in seen:
            cycles.append([u, v])
            seen.add((u, v))
    return sorted(cycles)


def compute_cascade_score(G: nx.DiGraph) -> dict[str, int]:
    """
    For each law, compute how many other laws would be affected if it were reformed.
    Defined as the number of nodes reachable via reverse edges from this node
    (i.e., how many laws cite this law, directly or indirectly).
    """
    # Reverse the graph so edges point from cited → citing
    G_rev = G.reverse()
    scores: dict[str, int] = {}
    for node in G.nodes():
        # Number of nodes reachable from this node in the reversed graph
        reachable = nx.single_source_shortest_path_length(G_rev, node)
        scores[node] = len(reachable) - 1  # exclude self
    return scores


def identify_isolated_laws(G: nx.DiGraph, degree_threshold: int = 2) -> list[str]:
    """
    Identify isolated or near-isolated laws (total degree below threshold).
    These may be obsolete or standalone laws.
    """
    isolated = []
    for node in G.nodes():
        total = G.in_degree(node) + G.out_degree(node)
        if total <= degree_threshold:
            isolated.append(node)
    return sorted(isolated)


def identify_hub_laws(G: nx.DiGraph, top_n: int = 20) -> list[tuple[str, float]]:
    """Return top N laws by PageRank (the most structurally central laws)."""
    pr = compute_pagerank(G)
    return sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_n]


def identify_authority_laws(G: nx.DiGraph, top_n: int = 20) -> list[tuple[str, int]]:
    """Return top N laws by in-degree (most frequently cited)."""
    by_indegree = [(node, G.in_degree(node)) for node in G.nodes()]
    return sorted(by_indegree, key=lambda x: x[1], reverse=True)[:top_n]


def compute_all_metrics(G: nx.DiGraph) -> dict[str, Any]:
    """
    Run the full suite of network metrics and return a comprehensive result dict.
    This is the main entry point for 06_build_graph.py.
    """
    print("Computing degree metrics...")
    degree_metrics = compute_degree_metrics(G)

    print("Computing PageRank...")
    pagerank = compute_pagerank(G)

    print("Computing betweenness centrality...")
    betweenness = compute_betweenness_centrality(G)

    print("Computing HITS...")
    hubs, authorities = compute_hits(G)

    print("Detecting communities...")
    communities = compute_community_louvain(G)

    print("Computing cascade scores...")
    cascade = compute_cascade_score(G)

    print("Finding circular dependencies...")
    cycles = find_circular_dependencies(G)

    # Merge everything per node
    node_metrics: dict[str, dict] = {}
    for node in G.nodes():
        node_metrics[node] = {
            **degree_metrics.get(node, {}),
            "pagerank": pagerank.get(node, 0.0),
            "betweenness": betweenness.get(node, 0.0),
            "hub_score": hubs.get(node, 0.0),
            "authority_score": authorities.get(node, 0.0),
            "community": communities.get(node, -1),
            "cascade_score": cascade.get(node, 0),
        }

    # Graph-level summary
    summary = {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": nx.density(G),
        "num_communities": len(set(communities.values())),
        "num_cycles": len(cycles),
        "num_isolated": len(identify_isolated_laws(G)),
        "top_hubs": identify_hub_laws(G, 10),
        "top_authorities": identify_authority_laws(G, 10),
        "circular_dependencies": cycles[:20],  # top 20 cycles
    }

    return {
        "node_metrics": node_metrics,
        "summary": summary,
    }


def graph_to_json_format(G: nx.DiGraph, node_metrics: dict[str, dict]) -> dict:
    """
    Convert graph + metrics to the JSON format expected by the D3.js frontend.
    """
    nodes = []
    for node, data in G.nodes(data=True):
        metrics = node_metrics.get(node, {})
        nodes.append({
            "id": node,
            "name": data.get("name", node),
            "short": data.get("short", ""),
            "sector": data.get("sector", ""),
            "in_degree": metrics.get("in_degree", 0),
            "out_degree": metrics.get("out_degree", 0),
            "pagerank": round(metrics.get("pagerank", 0.0), 6),
            "betweenness": round(metrics.get("betweenness", 0.0), 6),
            "community": metrics.get("community", -1),
            "cascade_score": metrics.get("cascade_score", 0),
            "url": data.get("url", ""),
        })

    links = []
    for source, target, data in G.edges(data=True):
        links.append({
            "source": source,
            "target": target,
            "confidence": data.get("confidence", "medium"),
            "citation_count": data.get("citation_count", 1),
            "sample_article": data.get("sample_article", ""),
        })

    return {"nodes": nodes, "links": links}
