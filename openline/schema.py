# openline/schema.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Tuple

import math
import networkx as nx
from pydantic import BaseModel, Field, field_validator, model_validator


# -------------------------
# Enums (wire-safe)
# -------------------------

class Gauge(str, Enum):
    sym = "sym"  # symbolic only
    emb = "emb"  # embedding/continuous coordinates


class NodeType(str, Enum):
    Claim = "Claim"
    Evidence = "Evidence"
    Counter = "Counter"
    Assumption = "Assumption"
    Constraint = "Constraint"
    PlanStep = "PlanStep"
    Outcome = "Outcome"
    Principle = "Principle"
    Motif = "Motif"


class EdgeRel(str, Enum):
    supports = "supports"
    contradicts = "contradicts"
    depends_on = "depends_on"
    derives = "derives"
    updates = "updates"
    instantiates = "instantiates"
    illustrates = "illustrates"


class MorphOpType(str, Enum):
    add_node = "add_node"
    add_edge = "add_edge"
    del_node = "del_node"
    del_edge = "del_edge"
    retype = "retype"
    reweight = "reweight"
    merge = "merge"
    split = "split"
    homotopy = "homotopy"


# -------------------------
# Core wire models
# -------------------------

class Node(BaseModel):
    """Graph node on the wire (shape payload)."""
    id: str
    type: NodeType  # Claim, Evidence, Counter, ...
    label: Optional[str] = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    attrs: Dict[str, str] = Field(default_factory=dict)


class Edge(BaseModel):
    """Directed, typed edge (shape payload)."""
    src: str
    dst: str
    rel: EdgeRel
    weight: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _no_self_loop(self) -> "Edge":
        if self.src == self.dst:
            # Self-loops tend to produce degenerate support cycles; keep forbidden by default.
            raise ValueError("Edge cannot be self-loop (src == dst)")
        return self


class Digest(BaseModel):
    """5-number 'shape fingerprint'."""
    b0: int = Field(ge=0)            # components
    cycle_plus: int = Field(ge=0)    # count of support cycles
    x_frontier: int = Field(ge=0)    # count of live contradictions
    s_over_c: float = Field(ge=0.0)  # support:contradiction ratio
    depth: int = Field(ge=0)         # longest depends_on chain length


class Telemetry(BaseModel):
    """Runtime dials (coherence, curvature, commutator, cost, determinism drift)."""
    phi_sem: float = Field(ge=0.0, le=1.0)
    phi_topo: float = Field(ge=0.0, le=1.0)
    delta_hol: float = Field(ge=0.0)   # L1 diff of digests across loop
    kappa_eff: float = Field(ge=0.0)   # effective curvature
    commutator: float = Field(ge=0.0)  # order-debt proxy
    cost_tokens: int = Field(ge=0)
    da_drift: float = Field(ge=0.0)    # determinism anchor drift (batch variance)


class MorphOp(BaseModel):
    """Operation-based CRDT 'liquid' change.

    Payload keys are validated lightly per op to keep implementation small but honest.
    """
    op: MorphOpType
    payload: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_payload(self) -> "MorphOp":
        p = self.payload
        if self.op == MorphOpType.add_node:
            if "node" not in p:
                raise ValueError("add_node requires payload.node")
        elif self.op == MorphOpType.add_edge:
            if not {"src", "dst", "rel"}.issubset(p.keys()):
                raise ValueError("add_edge requires payload.src,dst,rel")
        elif self.op in {MorphOpType.del_node}:
            if "id" not in p:
                raise ValueError("del_node requires payload.id")
        elif self.op in {MorphOpType.del_edge}:
            if not {"src", "dst", "rel"}.issubset(p.keys()):
                raise ValueError("del_edge requires payload.src,dst,rel")
        elif self.op == MorphOpType.retype:
            if not {"id", "new_type"}.issubset(p.keys()):
                raise ValueError("retype requires payload.id,new_type")
        elif self.op == MorphOpType.reweight:
            if "weight" not in p or not (0.0 <= float(p["weight"]) <= 1.0):
                raise ValueError("reweight requires payload.weight in [0,1]")
        elif self.op == MorphOpType.merge:
            if not {"ids", "into"}.issubset(p.keys()):
                raise ValueError("merge requires payload.ids (list), into (str)")
        elif self.op == MorphOpType.split:
            if not {"id", "into_ids"}.issubset(p.keys()):
                raise ValueError("split requires payload.id, into_ids (list)")
        elif self.op == MorphOpType.homotopy:
            # Flexible; allow {path|control_points|note}
            if not any(k in p for k in ("path", "control_points", "note")):
                raise ValueError("homotopy requires one of payload.path/control_points/note")
        return self


class Frame(BaseModel):
    """Open Line Protocol v0.1 frame: shape + liquid + telemetry + witness mark."""
    stream_id: str
    t_logical: int
    gauge: Gauge
    units: str

    nodes: List[Node]
    edges: List[Edge]
    digest: Digest

    morphs: List[MorphOp] = Field(default_factory=list)
    telem: Telemetry
    signature: Optional[str] = None

    # ---------- Structural validators ----------

    @field_validator("nodes")
    @classmethod
    def _unique_node_ids(cls, v: List[Node]) -> List[Node]:
        ids = [n.id for n in v]
        if len(ids) != len(set(ids)):
            dupes = {i for i in ids if ids.count(i) > 1}
            raise ValueError(f"Duplicate node ids: {sorted(dupes)}")
        return v

    @model_validator(mode="after")
    def _edges_reference_existing_nodes(self) -> "Frame":
        node_ids = {n.id for n in self.nodes}
        for e in self.edges:
            if e.src not in node_ids or e.dst not in node_ids:
                raise ValueError(f"Edge references unknown node: {e.src}->{e.dst}")
        return self


# -------------------------
# Digest & holonomy helpers
# -------------------------

def compute_digest(nodes: List[Node], edges: List[Edge]) -> Digest:
    """Compute the 5-number digest from the current graph."""
    # Build directed graph for typed edges
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n.id, type=n.type, weight=n.weight)
    for e in edges:
        G.add_edge(e.src, e.dst, rel=e.rel, weight=e.weight)

    # b0: weakly connected components
    b0 = nx.number_weakly_connected_components(G)

    # cycle_plus: number of simple cycles consisting only of 'supports' edges
    supports_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("rel") == EdgeRel.supports]
    Gs = nx.DiGraph()
    Gs.add_nodes_from(G.nodes)
    Gs.add_edges_from(supports_edges)
    try:
        cycle_plus = sum(1 for _ in nx.simple_cycles(Gs))
    except nx.NetworkXNoCycle:
        cycle_plus = 0

    # x_frontier: count of contradictions edges
    x_frontier = sum(1 for _, _, d in G.edges(data=True) if d.get("rel") == EdgeRel.contradicts)

    # s_over_c: support:contradiction ratio (safe when c == 0)
    s_count = len(supports_edges)
    c_count = x_frontier
    s_over_c = float(s_count) if c_count == 0 else float(s_count) / float(c_count)

    # depth: longest 'depends_on' chain (approx if cycles exist)
    deps_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get("rel") == EdgeRel.depends_on]
    depth = 0
    if deps_edges:
        D = nx.DiGraph()
        D.add_nodes_from(G.nodes)
        D.add_edges_from(deps_edges)
        if nx.is_directed_acyclic_graph(D):
            depth = nx.dag_longest_path_length(D)
        else:
            # Fallback: approximate with longest simple path search bounded by node count
            depth = min(len(D.nodes) - 1, 8)

    return Digest(b0=b0, cycle_plus=cycle_plus, x_frontier=x_frontier, s_over_c=s_over_c, depth=depth)


def holonomy_gap(pre: Digest, post: Digest) -> float:
    """L1 distance between digest vectors (Δ_hol)."""
    v1 = (pre.b0, pre.cycle_plus, pre.x_frontier, pre.s_over_c, pre.depth)
    v2 = (post.b0, post.cycle_plus, post.x_frontier, post.s_over_c, post.depth)
    return float(sum(abs(a - b) for a, b in zip(v1, v2)))


# -------------------------
# Guard checks
# -------------------------

class GuardConfig(BaseModel):
    cycle_plus_cap: int = 4
    delta_hol_cap: float = 2.0


class GuardError(ValueError):
    code: str


def _morph_adds_resolver(morphs: List[MorphOp]) -> bool:
    """Heuristic: did this frame add an Assumption/Counter node (i.e., resolved instead of erasing)?"""
    for m in morphs:
        if m.op == MorphOpType.add_node:
            node = m.payload.get("node")
            if isinstance(node, dict):
                t = node.get("type")
                if t in (NodeType.Assumption, NodeType.Counter, "Assumption", "Counter"):
                    return True
    return False


def guard_check(
    frame: Frame,
    *,
    prev_digest: Optional[Digest] = None,
    cfg: GuardConfig = GuardConfig(),
) -> None:
    """Enforce three protocol guards (raise ValueError with actionable message if violated)."""

    # (1) cycle_plus cap
    if frame.digest.cycle_plus > cfg.cycle_plus_cap:
        raise ValueError(
            f"Guard violation: cycle_plus={frame.digest.cycle_plus} exceeds cap={cfg.cycle_plus_cap} "
            "(self-reinforcing support loop)."
        )

    # (2) x_frontier must not drop by deletion-only
    if prev_digest is not None and frame.digest.x_frontier < prev_digest.x_frontier:
        # If any deletion morphs present AND no resolver nodes were added -> reject
        has_deletes = any(m.op in {MorphOpType.del_node, MorphOpType.del_edge} for m in frame.morphs)
        if has_deletes and not _morph_adds_resolver(frame.morphs):
            raise ValueError(
                "Guard violation: x_frontier (live contradictions) dropped via deletion only. "
                "Resolve by adding Assumption/Counter, not by erasure."
            )

    # (3) Δ_hol spike without explanatory node
    if prev_digest is not None:
        delta = holonomy_gap(prev_digest, frame.digest)
        if frame.telem.delta_hol < 0:
            raise ValueError("Telemetry.delta_hol must be non-negative")
        # Prefer using computed delta for truth; telem.delta_hol is advisory
        if delta > cfg.delta_hol_cap and not _morph_adds_resolver(frame.morphs):
            raise ValueError(
                f"Guard violation: Δ_hol={delta:.2f} exceeds cap={cfg.delta_hol_cap:.2f} "
                "without an accompanying Assumption/Counter node explaining the jump."
            )


# -------------------------
# JSON Schema helper
# -------------------------

def frame_json_schema() -> Dict[str, Any]:
    """Return the JSON Schema for Frame (wire contract)."""
    return Frame.model_json_schema()
# --- Telemetry & BusReply (for FastAPI response) ---
from pydantic import BaseModel, Field  # ok if already imported above

class Telemetry(BaseModel):
    phi_sem: float = Field(0.0, ge=0.0, le=1.0)
    phi_topo: float = Field(0.0, ge=0.0, le=1.0)
    delta_hol: float = Field(0.0, ge=0.0)
    kappa_eff: float = Field(0.0, ge=0.0)
    commutator: float = Field(0.0, ge=0.0)
    cost_tokens: int = Field(0, ge=0)
    da_drift: float = Field(0.0, ge=0.0)

class BusReply(BaseModel):
    ok: bool
    digest: Digest
    telem: Telemetry
