# openline/schema.py
from __future__ import annotations

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# --------------------------
# Core wire models
# --------------------------

class Node(BaseModel):
    id: str
    type: str  # Claim, Evidence, Counter, Assumption, Constraint, PlanStep, Outcome, Principle, Motif
    label: Optional[str] = None
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    attrs: Dict[str, str] = Field(default_factory=dict)


class Edge(BaseModel):
    src: str
    dst: str
    rel: str  # supports | contradicts | depends_on | derives | updates | instantiates | illustrates
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class Digest(BaseModel):
    b0: int
    cycle_plus: int
    x_frontier: int
    s_over_c: float
    depth: int


class Telemetry(BaseModel):
    phi_sem: float = Field(0.0, ge=0.0, le=1.0)
    phi_topo: float = Field(0.0, ge=0.0, le=1.0)
    delta_hol: float = Field(0.0, ge=0.0)
    kappa_eff: float = Field(0.0, ge=0.0)
    commutator: float = Field(0.0, ge=0.0)
    cost_tokens: int = Field(0, ge=0)
    da_drift: float = Field(0.0, ge=0.0)  # determinism-anchor drift (optional future use)


class Frame(BaseModel):
    stream_id: str
    t_logical: int
    gauge: str  # e.g., "sym" | "emb:all-MiniLM" etc.
    units: str  # human hint like "confidence:0..1,cost:tokens"
    nodes: List[Node]
    edges: List[Edge]
    digest: Digest
    morphs: List[Dict] = Field(default_factory=list)   # op-based CRDT entries
    telem: Telemetry = Field(default_factory=Telemetry)
    signature: Optional[str] = None  # witness mark (Merkle/signature)


class BusReply(BaseModel):
    ok: bool
    digest: Digest
    telem: Telemetry
