# openline/guards.py
from __future__ import annotations

from typing import Optional, Dict, Any, List

from openline.schema import Frame, Digest
from openline.digest import holonomy_gap

# Defaults (you can tune later)
CYCLE_PLUS_CAP = 4
DELTA_HOL_CAP = 2.0

def _adds_resolver(morphs: List[Dict[str, Any]]) -> bool:
    """
    Heuristic: did this frame add an Assumption/Counter node?
    We look for a morph like {"op": "add_node", "node": {"type": "Assumption"|"Counter", ...}}
    This matches your simple Dict-based 'morphs' in schema.py.
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
        # If there are any deletion morphs AND no resolver node was added → reject
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
