#!/usr/bin/env python3
"""
FlowState Lite Example
OpenLine Protocol demo for multi-scale consistency receipts.
"""

import argparse
import json
import httpx
from pathlib import Path
from typing import List, Dict, Any

# ---------- Helpers ----------

def parse_inline_array(array_str: str) -> List[float]:
    """Parse inline CSV/JSON/space arrays into list of floats."""
    array_str = array_str.strip()
    if not array_str:
        return []
    try:
        if array_str.startswith("[") and array_str.endswith("]"):
            return [float(x) for x in json.loads(array_str)]
        if "," in array_str:
            return [float(x) for x in array_str.split(",")]
        return [float(x) for x in array_str.split()]
    except Exception:
        raise ValueError(f"Invalid array format: {array_str}")

def load_file(path: str) -> List[float]:
    """Load CSV or JSON file with numeric values."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if p.suffix == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return [float(x) for x in data]
        for key in ["values", "data", "price", "close"]:
            if key in data:
                return [float(x) for x in data[key]]
        raise ValueError(f"No numeric array found in {path}")
    if p.suffix == ".csv":
        return [float(line.strip().split(",")[0]) for line in p.read_text().splitlines() if line.strip()]
    raise ValueError(f"Unsupported file type: {path}")

def delta_scale(path_a: List[float], path_b: List[float]) -> float:
    """Compute normalized scale difference."""
    if not path_a or not path_b or len(path_a) != len(path_b):
        return 0.0
    diffs = [abs(a - b) for a, b in zip(path_a, path_b)]
    denom = sum(abs(b) for b in path_b) / len(path_b)
    return (sum(diffs) / len(diffs)) / (denom + 1e-9)

# ---------- Frame Builders ----------

def build_sync(stream_id: str, model: str, asset_class: str, scale_pairs: List[str]) -> Dict[str, Any]:
    return {
        "stream_id": stream_id,
        "t_logical": 1,
        "nodes": [{
            "id": "C1",
            "type": "Claim",
            "label": f"{model} multi-scale forecast ({asset_class})",
            "attrs": {"scales": scale_pairs}
        }],
        "edges": []
    }

def build_measure(sync: Dict[str, Any], violations: Dict[str, float]) -> Dict[str, Any]:
    frame = sync.copy()
    frame["t_logical"] = 2
    for i, (pair, d) in enumerate(violations.items(), 1):
        nid = f"X{i}"
        frame["nodes"].append({
            "id": nid,
            "type": "Counter",
            "label": f"{pair} drift Δ={d:.3f}"
        })
        frame["edges"].append({"src": nid, "dst": "C1", "rel": "contradicts"})
    return frame

def build_stitch(measure: Dict[str, Any], realized: float) -> Dict[str, Any]:
    frame = measure.copy()
    frame["t_logical"] = 3
    frame["nodes"].append({
        "id": "E_outcome",
        "type": "Evidence",
        "label": f"Realized move {realized:+.2%}"
    })
    frame["edges"].append({"src": "E_outcome", "dst": "C1", "rel": "supports"})
    return frame

def post_frame(frame: Dict[str, Any], url: str):
    r = httpx.post(url, json=frame, timeout=30)
    r.raise_for_status()
    return r.json()

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8088/frame")
    ap.add_argument("--stream-id", default="fs-lite-demo")
    ap.add_argument("--model", default="ibm-research/flowstate-r1")
    ap.add_argument("--asset-class", default="equity")
    ap.add_argument("--scale-pair", action="append", help="e.g. min->hour")
    ap.add_argument("--path-a", action="append")
    ap.add_argument("--path-b", action="append")
    ap.add_argument("--path-a-file", action="append")
    ap.add_argument("--path-b-file", action="append")
    ap.add_argument("--realized-move", type=float)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    scale_data = {}
    if args.scale_pair:
        for i, pair in enumerate(args.scale_pair):
            if args.path_a and args.path_b and i < len(args.path_a) and i < len(args.path_b):
                pa = parse_inline_array(args.path_a[i])
                pb = parse_inline_array(args.path_b[i])
            elif args.path_a_file and args.path_b_file and i < len(args.path_a_file) and i < len(args.path_b_file):
                pa = load_file(args.path_a_file[i])
                pb = load_file(args.path_b_file[i])
            else:
                continue
            scale_data[pair] = (pa, pb)

    # Build frames
    sync = build_sync(args.stream_id, args.model, args.asset_class, list(scale_data.keys()))
    violations = {pair: delta_scale(pa, pb) for pair, (pa, pb) in scale_data.items() if delta_scale(pa, pb) > 0.05}
    measure = build_measure(sync, violations) if violations else sync
    frames = [sync, measure]
    if args.realized_move is not None:
        frames.append(build_stitch(measure, args.realized_move))

    # Print and post
    for f in frames:
        print(json.dumps(f, indent=2))
        if not args.dry_run:
            resp = post_frame(f, args.url)
            print("Posted:", resp)

if __name__ == "__main__":
    main()
