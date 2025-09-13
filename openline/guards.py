# openline/guards.py
from __future__ import annotations

from typing import Optional, Dict, Any, List

from openline.schema import Frame, Digest
from openline.digest import holonomy_gap

# --- tuned Δ_scale caps loader (reads data/params.json; auto-invalidates) ---
import json, time
from pathlib import Path

_PARAMS_PATH = Path("data/params.json")
_PARAMS_CACHE = {"ts": 0.0, "mtime": None, "data": {"scale_caps": {}}}

def _load_params(ttl: float = 60.0):
    """Return latest params; if file is gone or changed, refresh immediately.
    If unchanged and within ttl, return cached."""
    now = time.time()
    exists = _PARAMS_PATH.exists()
    mtime = _PARAMS_PATH.stat().st_mtime if exists else None

    # reuse cache only if file state/mtime unchanged AND within TTL
    if (now - _PARAMS_CACHE["ts"] < ttl) and (_PARAMS_CACHE["mtime"] == mtime):
        return _PARAMS_CACHE["data"]

    if not exists:
        _PARAMS_CACHE.update({"ts": now, "mtime": None, "data": {"scale_caps": {}}})
        return _PARAMS_CACHE["data"]

    try:
        data = json.loads(_PARAMS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {"scale_caps": {}}
    except Exception:
        data = {"scale_caps": {}}  # corrupt file → safe default

    _PARAMS_CACHE.update({"ts": now, "mtime": mtime, "data": data})
    return _PARAMS_CACHE["data"]

def tuned_cap(asset: str, pair: str, default_cap: float):
    """Look up learned cap; fall back to provided default if missing."""
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

# Defaults (you can tune later)
CYCLE_PLUS_CAP = 4
DELTA_HOL_CAP = 2.0

def _adds_resolver(morphs: List[Dict[str, Any]]) -> bool:
    """
    Heuristic: did this frame add an Assumption/Counter node?
    We look for a morph like {"op": "add_node", "node": {"type": "Assumption"|"Counter", ...}}
    """
    for m in morphs:
        if m.get("op") == "add_node":
            node = m.get("node") or m.get("payload", {}).get("node")
            if isinstance(node, dict):
                t = node.get("type")
                if t in ("Assumption", "Counter"):
                    return True
    return False

def guard_check(frame: Frame, *, prev_digest: Optional[Digest] = None) -> None:
    """
    Enforce three protocol guards.
    Raises ValueError with an actionable message if any guard fails.
    Assumes frame.digest has been recomputed by the bus.
    """
    d = frame.digest

    # 1) Cycle cap
    if d.cycle_plus > CYCLE_PLUS_CAP:
        raise ValueError(
            f"cycle_plus={d.cycle_plus} exceeds cap={CYCLE_PLUS_CAP} "
            "(self-reinforcing support loop)."
        )

    # 2) Frontier deletion (x_frontier must not drop via deletions-only)
    if prev_digest is not None and d.x_frontier < prev_digest.x_frontier:
        has_deletes = any(m.get("op") in ("del_node", "del_edge") for m in frame.morphs)
        if has_deletes and not _adds_resolver(frame.morphs):
            raise ValueError(
                "x_frontier decreased via deletions only. "
                "Resolve contradictions by adding an Assumption/Counter, not by erasing edges/nodes."
            )

    # 3) Holonomy spike without explanation
    if prev_digest is not None:
        delta = holonomy_gap(prev_digest, d)
        if delta > DELTA_HOL_CAP and not _adds_resolver(frame.morphs):
            raise ValueError(
                f"Δ_hol={delta:.2f} exceeds cap={DELTA_HOL_CAP:.2f} "
                "without an Assumption/Counter explaining the jump."
            )

DELTA_SCALE_CAP_DEFAULT = 0.03
ASSET_CAPS = {"equity":0.03, "fx":0.015, "crypto":0.12, "commodity":0.04, "bond":0.01}

def _has_explanation(frame):
    nodes = getattr(frame, "nodes", None) or frame.get("nodes", []) or []
    edges = getattr(frame, "edges", None) or frame.get("edges", []) or []
    for n in nodes:
        if n.get("type") in ("Assumption","Counter"):
            return True
    for e in edges:
        if e.get("rel") in ("contradicts","supports"):
            return True
    telem = getattr(frame, "telem", None) or frame.get("telem", {}) or {}
    tol = telem.get("delta_scale_tolerance")
    return isinstance(tol, (int,float)) and tol >= 0

def guard_check(frame):
    telem = getattr(frame, "telem", None) or frame.get("telem", {}) or {}
    ds = float(telem.get("delta_scale", 0.0))
    attrs = {}
    for n in (getattr(frame, "nodes", None) or frame.get("nodes", []) or []):
        if n.get("type") == "Claim":
            attrs = n.get("attrs", {}) or {}
            break
    asset = (attrs.get("asset_class") or "default").lower()
    pair  = (attrs.get("cadence_pair") or "").strip()
    cap = ASSET_CAPS.get(asset, DELTA_SCALE_CAP_DEFAULT)
    pair_caps = {"min↔hour": cap, "hour↔day": cap*1.2, "day↔week": cap*1.6}
    cap_eff = pair_caps.get(pair, cap)
    cap_eff = tuned_cap(asset, pair, cap_eff)  # ← use learned cap if present
    if ds and ds > cap_eff and not _has_explanation(frame):
        raise ValueError(f"Δ_scale={ds:.3f} exceeds cap={cap_eff:.3f} without Counter/Assumption/edge/tolerance")
