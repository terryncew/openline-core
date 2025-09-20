#!/usr/bin/env python3
# Minimal JSON-RPC 2.0 stdin/stdout server exposing method: openline.stitch
# No deps. Intended to be dropped into any repo.

import sys, json, time
from typing import Any, Dict, List, Set, Tuple

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _node_ids(nodes: List[Dict[str, Any]]) -> Set[str]:
    return {n.get("id", "") for n in nodes if isinstance(n, dict)}

def _count_cycles(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> int:
    # simple directed cycle count (detect back-edges)
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

def validate_and_receipt(frame: Dict[str, Any]):
    errs: List[str] = []
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
    telemetry.setdefault("holonomy", cycles)  # simple proxy
    frame["telemetry"] = telemetry

    receipt = {
        "id": f"rcpt-{int(time.time())}",
        "ts": _now_iso(),
        "actor": "openline.mcp.stub",
        "frame_id": frame.get("id", ""),
        "status": "ok" if not errs else "guard_violated",
        "point": "Frame validated and stitched." if not errs else "Frame violated guard(s).",
        "because": f"{n_nodes} nodes, {n_edges} edges; cycles={cycles}; contradictions={contras}",
        "but": "; ".join(errs) if errs else "",
        "so": "Proceed to next step." if not errs else "Fix references/structure and retry.",
        "digest": { "n_nodes": n_nodes, "n_edges": n_edges, "cycles": cycles, "contradictions": contras }
    }
    return receipt

def handle_rpc(req: Dict[str, Any]) -> Dict[str, Any]:
    rid = req.get("id"); method = req.get("method"); params = req.get("params") or {}
    if method == "openline.stitch":
        frame = params.get("frame") or {}
        receipt = validate_and_receipt(frame)
        return {"jsonrpc":"2.0","id":rid,"result":receipt}
    return {"jsonrpc":"2.0","id":rid,"error":{"code":-32601,"message":"Method not found"}}

def main():
    # Line-delimited JSON-RPC; one request per line.
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try:
            req = json.loads(line)
            resp = handle_rpc(req)
        except Exception as e:
            resp = {"jsonrpc":"2.0","id":None,"error":{"code":-32000,"message":str(e)}}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
