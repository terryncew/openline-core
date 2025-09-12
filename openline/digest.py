# openline/digest.py
from __future__ import annotations

from typing import List, Optional
import networkx as nx

from openline.schema import Node, Edge, Digest

SUPPORT = "supports"
CONTRA = "contradicts"
DEP = "depends_on"

def compute_digest(nodes: List[Node], edges: List[Edge]) -> Digest:
    """
    Compute the 5-number digest:
      - b0: connected components (weak connectivity)
      - cycle_plus: count of simple cycles using only 'supports' edges
      - x_frontier: number of 'contradicts' edges (live contradictions)
      - s_over_c: supports : contradictions ratio (safe when c==0)
      - depth: longest dependency chain ('depends_on' treated as DAG if possible)
    """
    # Build directed graph with edge rel
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n.id)
    for e in edges:
        G.add_edge(e.src, e.dst, rel=e.rel)

    # b0: weakly connected components
    b0 = nx.number_weakly_connected_components(G) if G.number_of_nodes() else 0

    # cycle_plus: cycles on supports-only subgraph
    Gs = nx.DiGraph()
    Gs.add_nodes_from(G.nodes)
    for u, v, d in G.edges(data=True):
        if d.get("rel") == SUPPORT:
            Gs.add_edge(u, v)
    try:
        cycle_plus = sum(1 for _ in nx.simple_cycles(Gs))
    except nx.NetworkXNoCycle:
        cycle_plus = 0

    # x_frontier: count contradiction edges
    x_frontier = sum(1 for _, _, d in G.edges(data=True) if d.get("rel") == CONTRA)

    # s_over_c: ratio
    s_count = Gs.number_of_edges()
    c_count = x_frontier
    s_over_c = float(s_count) if c_count == 0 else float(s_count) / float(c_count)

    # depth: longest depends_on chain
    D = nx.DiGraph()
    D.add_nodes_from(G.nodes)
    for u, v, d in G.edges(data=True):
        if d.get("rel") == DEP:
            # interpret "A depends_on B" as B -> A for depth
            D.add_edge(v, u)
    if D.number_of_edges() == 0:
        depth = 0
    elif nx.is_directed_acyclic_graph(D):
        depth = int(nx.dag_longest_path_length(D))
    else:
        # If there are cycles, approximate with a capped search
        depth = min(len(D.nodes) - 1, 8)

    return Digest(b0=b0, cycle_plus=cycle_plus, x_frontier=x_frontier, s_over_c=s_over_c, depth=depth)

def holonomy_gap(pre: Optional[Digest], post: Digest) -> float:
    """L1 distance between digests (Δ_hol). None → 0.0."""
    if pre is None:
        return 0.0
    v1 = (pre.b0, pre.cycle_plus, pre.x_frontier, pre.s_over_c, pre.depth)
    v2 = (post.b0, post.cycle_plus, post.x_frontier, post.s_over_c, post.depth)
    return float(sum(abs(a - b) for a, b in zip(v1, v2)))
