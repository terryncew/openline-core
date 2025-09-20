from typing import Any, Dict, List, Set, Tuple
import time

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _node_ids(nodes: List[Dict[str, Any]]) -> Set[str]:
    return {n.get("id", "") for n in nodes if isinstance(n, dict)}

def _count_cycles(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> int:
    g: Dict[str, List[str]] = {}
    for n in nodes:
        nid = n.get("id")
        if nid:
            g[nid] = []
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a in g and b in g:
            g[a].append(b)
    seen, stack = set(), set()
    cycles = 0
    def dfs(u: str):
        nonlocal cycles
        seen.add(u); stack.add(u)
        for v in g.get(u, []):
            if v not in seen:
                dfs(v)
            elif v in stack:
                cycles += 1
        stack.remove(u)
    for nid in g.keys():
        if nid not in seen:
            dfs(nid)
    return cycles

def _contradictions(edges: List[Dict[str, Any]]) -> int:
    return sum(1 for e in edges if e.get("type") == "contradicts")

def _density(n_nodes: int, n_edges: int) -> float:
    max_edges = max(1, n_nodes * (n_nodes - 1) // 2)
    return round(n_edges / max_edges, 4)

def _validate_frame(frame: Dict[str, Any]):
    errs = []
    nodes = frame.get("nodes") or []
    edges = frame.get("edges") or []
    if not isinstance(nodes, list) or not nodes:
        errs.append("nodes must be a non-empty array")
    if not isinstance(edges, list):
        errs.append("edges must be an array")
    ids = _node_ids(nodes)
    for e in edges:
        if e.get("from") not in ids or e.get("to") not in ids:
            errs.append(f"edge references missing node: {e}")

    n_nodes = len(ids)
    n_edges = len(edges)
    cycles = _count_cycles(nodes, edges)
    contras = _contradictions(edges)
    dens = _density(n_nodes, n_edges)

    telemetry = frame.get("telemetry") or {}
    telemetry.setdefault("shape", [n_nodes, n_edges, dens, cycles, contras])
    telemetry.setdefault("holonomy", cycles)
    frame["telemetry"] = telemetry
    return frame, errs

def olp_guard_node(state: Dict[str, Any]) -> Dict[str, Any]:
    frame = state.get("frame") or {}
    frame, errs = _validate_frame(frame)
    shape = frame["telemetry"]["shape"]
    receipt = {
        "id": f"rcpt-{int(time.time())}",
        "ts": _now_iso(),
        "actor": "openline.langgraph.guard",
        "frame_id": frame.get("id", ""),
        "status": "ok" if not errs else "guard_violated",
        "point": "Frame validated." if not errs else "Frame violated guard(s).",
        "because": f"shape={shape}",
        "but": "; ".join(errs) if errs else "",
        "so": "Continue." if not errs else "Fix frame and retry.",
        "digest": {
            "n_nodes": shape[0],
            "n_edges": shape[1],
            "cycles": shape[3],
            "contradictions": shape[4]
        }
    }
    state = dict(state)
    state["frame"] = frame
    state["receipt"] = receipt
    return state
