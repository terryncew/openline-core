# openline/guards.py
from __future__ import annotations

from typing import Optional, Dict, Any, Iterable, List, Union

from openline.schema import Frame, Digest
from openline.digest import holonomy_gap

# ----------------------------
# Tuned Δ_scale caps (data/params.json) with mtime-aware cache
# ----------------------------
import json, time
from pathlib import Path

_PARAMS_PATH = Path("data/params.json")
_PARAMS_CACHE: Dict[str, Any] = {"ts": 0.0, "mtime": None, "data": {"scale_caps": {}}}

def _load_params(ttl: float = 60.0) -> Dict[str, Any]:
    """
    Return latest params, refreshing when:
      - file mtime changed, or
      - TTL expired, or
      - file missing/corrupt (falls back to empty scale_caps)
    """
    now = time.time()
    exists = _PARAMS_PATH.exists()
    mtime = _PARAMS_PATH.stat().st_mtime if exists else None

    # Reuse cache only if within TTL AND mtime unchanged
    if (now - _PARAMS_CACHE["ts"] < ttl) and (_PARAMS_CACHE["mtime"] == mtime):
        return _PARAMS_CACHE["data"]

    if not exists:
        data = {"scale_caps": {}}
    else:
        try:
            data = json.loads(_PARAMS_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = {"scale_caps": {}}
        except Exception:
            data = {"scale_caps": {}}

    _PARAMS_CACHE.update({"ts": now, "mtime": mtime, "data": data})
    return data

def tuned_cap(asset: str, pair: str, default_cap: float) -> float:
    """
    Look up a learned cap for (asset, pair). Falls back to default_cap.
    """
    params = _load_params()
    cap = (
        params.get("scale_caps", {})
        .get((asset or "default").lower(), {})
        .get(pair or "")
    )
    try:
        return float(cap) if cap is not None else float(default_cap)
    except Exception:
        return float(default_cap)

# ----------------------------
# Guard constants
# ----------------------------
CYCLE_PLUS_CAP = 4
DELTA_HOL_CAP = 2.0

DELTA_SCALE_CAP_DEFAULT = 0.03
ASSET_CAPS = {
    "equity": 0.03,
    "fx": 0.015,
    "crypto": 0.12,
    "commodity": 0.04,
    "bond": 0.01,
}

# ----------------------------
# Utilities for dict / model frames
# ----------------------------
def _get(obj: Any, name: str, default: Any = None) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default

def _iter_nodes(frame_like: Any) -> Iterable[Dict[str, Any]]:
    nodes = _get(frame_like, "nodes", []) or []
    return nodes

def _iter_edges(frame_like: Any) -> Iterable[Dict[str, Any]]:
    edges = _get(frame_like, "edges", []) or []
    return edges

def _iter_morphs(frame_like: Any) -> Iterable[Dict[str, Any]]:
    morphs = _get(frame_like, "morphs", []) or []
    return morphs

def _adds_resolver(morphs: List[Dict[str, Any]]) -> bool:
    """
    Heuristic: did this frame add an Assumption or Counter?
    Looks for {"op":"add_node","node":{"type":"Assumption"|"Counter",...}}
    """
    for m in morphs:
        if m.get("op") == "add_node":
            node = m.get("node") or m.get("payload", {}).get("node")
            if isinstance(node, dict) and node.get("type") in ("Assumption", "Counter"):
                return True
    return False

def _has_explanation(frame_like: Any) -> bool:
    # nodes / edges explanation
    for n in _iter_nodes(frame_like):
        if n.get("type") in ("Assumption", "Counter"):
            return True
    for e in _iter_edges(frame_like):
        if e.get("rel") in ("contradicts", "supports"):
            return True
    # explicit tolerance in telem
    telem = _get(frame_like, "telem", {}) or {}
    tol = telem.get("delta_scale_tolerance")
    return isinstance(tol, (int, float)) and tol >= 0

# ----------------------------
# Main guard
# ----------------------------
def guard_check(frame: Union[Frame, Dict[str, Any]], *, prev_digest: Optional[Digest] = None) -> None:
    """
    Enforce protocol guards:
      1) cycle_plus cap
      2) frontier deletion (no drop in x_frontier via deletes-only without resolver)
      3) holonomy spike
      4) Δ_scale cap (with tuned override per asset/pair)
    Assumes frame.digest has been recomputed by the bus.
    """
    # --- digest (supports model or dict) ---
    d = _get(frame, "digest")
    if d is None:
        raise ValueError("frame.digest is required for guard_check")

    # 1) Cycle cap
    cycle_plus = _get(d, "cycle_plus", 0)
    if cycle_plus > CYCLE_PLUS_CAP:
        raise ValueError(
            f"cycle_plus={cycle_plus} exceeds cap={CYCLE_PLUS_CAP} "
            "(self-reinforcing support loop)."
        )

    # 2) Frontier deletion
    if prev_digest is not None:
        x_prev = _get(prev_digest, "x_frontier", None)
        x_curr = _get(d, "x_frontier", None)
        if x_prev is not None and x_curr is not None and x_curr < x_prev:
            has_deletes = any(m.get("op") in ("del_node", "del_edge") for m in _iter_morphs(frame))
            if has_deletes and not _adds_resolver(list(_iter_morphs(frame))):
                raise ValueError(
                    "x_frontier decreased via deletions only. "
                    "Resolve contradictions by adding an Assumption/Counter, not by erasing edges/nodes."
                )

    # 3) Holonomy spike
    if prev_digest is not None:
        try:
            delta_h = holonomy_gap(prev_digest, d)
        except Exception:
            delta_h = 0.0  # if shapes differ, don't trip this guard
        if delta_h > DELTA_HOL_CAP and not _adds_resolver(list(_iter_morphs(frame))):
            raise ValueError(
                f"Δ_hol={delta_h:.2f} exceeds cap={DELTA_HOL_CAP:.2f} "
                "without an Assumption/Counter explaining the jump."
            )

    # 4) Δ_scale cap (with tuned override)
    telem = _get(frame, "telem", {}) or {}
    ds = float(telem.get("delta_scale", 0.0) or 0.0)

    # pull asset/pair from first Claim node
    attrs: Dict[str, Any] = {}
    for n in _iter_nodes(frame):
        if n.get("type") == "Claim":
            attrs = n.get("attrs", {}) or {}
            break

    asset = (attrs.get("asset_class") or "default").lower()
    pair = (attrs.get("cadence_pair") or "").strip()

    base_cap = ASSET_CAPS.get(asset, DELTA_SCALE_CAP_DEFAULT)
    pair_caps = {
        "min↔hour": base_cap,
        "hour↔day": base_cap * 1.2,
        "day↔week": base_cap * 1.6,
    }
    cap_eff = pair_caps.get(pair, base_cap)
    cap_eff = tuned_cap(asset, pair, cap_eff)  # learned override if present

    if ds and (ds > cap_eff) and not _has_explanation(frame):
        raise ValueError(
            f"Δ_scale={ds:.3f} exceeds cap={cap_eff:.3f} "
            "without Counter/Assumption/edge/tolerance"
        )
