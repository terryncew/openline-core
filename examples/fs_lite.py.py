#!/usr/bin/env python3
"""
FlowState multi-scale receipts (v2-lite) for OpenLine Protocol

- No schema changes. Metrics go in node.attrs.
- Posts SYNC → MEASURE → (optional) STITCH to your running /frame bus.
- Asset-class thresholds + simple regime option, but minimal dependencies.

Usage (demo data):
    python examples/flowstate_v2_lite.py --asset-class equity

With inline arrays:
    python examples/flowstate_v2_lite.py \
      --scale-pair "min->hour" --path-a "100,101,99,102" --path-b "100,100.8,99.5,101.5"

Start your bus first:
    uv run olp-server
"""
import argparse
import copy
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

# ----------------------------
# Config
# ----------------------------
ASSET_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "equity":     {"min_hour": 0.02,  "hour_day": 0.035, "day_week": 0.05},
    "fx":         {"min_hour": 0.008, "hour_day": 0.015, "day_week": 0.025},
    "crypto":     {"min_hour": 0.08,  "hour_day": 0.12,  "day_week": 0.18},
    "commodity":  {"min_hour": 0.025, "hour_day": 0.04,  "day_week": 0.06},
    "bond":       {"min_hour": 0.005, "hour_day": 0.01,  "day_week": 0.015},
    "default":    {"min_hour": 0.03,  "hour_day": 0.05,  "day_week": 0.08},
}

SCALE_ORDER = ["tick", "min", "hour", "day", "week", "month", "quarter", "year"]

# ----------------------------
# Helpers
# ----------------------------
def parse_array(s: str) -> List[float]:
    s = (s or "").strip()
    if not s:
        return []
    if s.startswith("[") and s.endswith("]"):
        data = json.loads(s)
        return [float(x) for x in data]
    if "," in s:
        return [float(x.strip()) for x in s.split(",") if x.strip()]
    return [float(s)]

def load_series(path: str) -> List[float]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {p}")
    if p.suffix.lower() == ".json":
        with p.open() as f:
            data = json.load(f)
        if isinstance(data, list):
            return [float(x) for x in data]
        if isinstance(data, dict):
            for k in ["values", "data", "close", "price"]:
                if k in data and isinstance(data[k], list):
                    return [float(x) for x in data[k]]
            raise ValueError(f"JSON has no array-like timeseries at keys {list(data.keys())}")
        return [float(data)]
    elif p.suffix.lower() == ".csv":
        vals: List[float] = []
        with p.open(newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    try:
                        vals.append(float(cell))
                        break
                    except ValueError:
                        continue
        if not vals:
            raise ValueError("CSV contained no numeric cells")
        return vals
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")

def parse_pair(pair: str) -> Tuple[str, str]:
    for sep in ["→", "->", "-->", "=>"]:
        if sep in pair:
            a, b = pair.split(sep, 1)
            return a.strip(), b.strip()
    raise ValueError(f"Bad scale pair: {pair}")

def scale_distance(a: str, b: str) -> int:
    try:
        ia, ib = SCALE_ORDER.index(a), SCALE_ORDER.index(b)
        return abs(ib - ia)
    except ValueError:
        return 1

def pick_threshold(asset: str, scale_from: str, scale_to: str) -> float:
    tbl = ASSET_THRESHOLDS.get(asset, ASSET_THRESHOLDS["default"])
    dist = scale_distance(scale_from, scale_to)
    if dist == 1:
        return tbl.get("min_hour", 0.03)
    if dist == 2:
        return tbl.get("hour_day", 0.05)
    return tbl.get("day_week", 0.08)

def delta_scale(path_a: List[float], path_b: List[float]) -> Tuple[float, float, float, int]:
    n = min(len(path_a), len(path_b))
    if n == 0:
        return 0.0, 0.0, 1.0, 0
    diffs = [abs(path_a[i] - path_b[i]) for i in range(n)]
    mean_abs_b = sum(abs(path_b[i]) for i in range(n)) / n if n else 0.0
    if mean_abs_b < 1e-9:
        return 0.0, 0.0, 1.0, n
    ds = (sum(diffs) / n) / (mean_abs_b + 1e-9)
    md = (max(diffs) if diffs else 0.0) / (mean_abs_b + 1e-9)
    mr = (sum(path_a[:n]) / n) / ((sum(path_b[:n]) / n) + 1e-9)
    return float(ds), float(md), float(mr), n

# ----------------------------
# Frames
# ----------------------------
def make_sync(stream_id: str, asset: str, model: str, metrics: Dict[str, dict]) -> dict:
    nodes = [{
        "id": "C1",
        "type": "Claim",
        "label": f"FlowState multi-scale forecast ({asset})",
        "weight": 0.78,
        "attrs": {
            "asset_class": asset,
            "model": model,
            "scales_tested": list(metrics.keys()),
            "decode_basis": "FBD:K=64",
            "t0": datetime.now(timezone.utc).isoformat(),
            "total_scale_pairs": len(metrics),
        },
    }]
    edges: List[dict] = []
    for i, (pair, m) in enumerate(metrics.items(), 2):
        nodes.append({
            "id": f"E{i}",
            "type": "Evidence",
            "label": f"Scale context {pair}",
            "weight": 0.85,
            "attrs": {
                "scale_pair": pair,
                "n_points": m["n_points"],
                "threshold": m["threshold"],
            },
        })
        edges.append({"src": f"E{i}", "dst": "C1", "rel": "supports", "weight": 0.85})
    return {
        "stream_id": stream_id,
        "t_logical": 1,
        "gauge": "sym",
        "units": "confidence:0..1,cost:tokens",
        "nodes": nodes,
        "edges": edges,
        "digest": {"b0": 0, "cycle_plus": 0, "x_frontier": 0, "s_over_c": 0.0, "depth": 0},
        "morphs": [],
        "telem": {
            "phi_sem": 0.72, "phi_topo": 0.66, "delta_hol": 0.0,
            "kappa_eff": 0.30, "commutator": 0.0, "cost_tokens": 0, "da_drift": 0.0,
        },
        "signature": None,
    }

def make_measure(sync_frame: dict, metrics: Dict[str, dict]) -> dict:
    f = copy.deepcopy(sync_frame)
    f["t_logical"] = 2
    f["morphs"] = []
    violations = 0
    for i, (pair, m) in enumerate(metrics.items(), 1):
        if m["delta_scale"] <= m["threshold"] or m["n_points"] == 0:
            continue
        violations += 1
        x_id = f"X{i}"
        f["nodes"].append({
            "id": x_id,
            "type": "Counter",
            "label": f"Scale drift {pair}: Δ={m['delta_scale']:.3f} > {m['threshold']:.3f}",
            "weight": 0.8,
            "attrs": {
                "scale_pair": pair,
                "delta_scale": m["delta_scale"],
                "max_deviation": m["max_deviation"],
                "mean_ratio": m["mean_ratio"],
                "threshold": m["threshold"],
            },
        })
        f["edges"].append({"src": x_id, "dst": "C1", "rel": "contradicts", "weight": 0.8})
        f["morphs"].extend([
            {"op": "add_node", "node": {"id": x_id, "type": "Counter"}},
            {"op": "add_edge", "src": x_id, "dst": "C1", "rel": "contradicts"},
        ])
    # One tolerance assumption if any violations
    if violations:
        a_id = "A1"
        f["nodes"].append({
            "id": a_id,
            "type": "Assumption",
            "label": f"Tolerance: {violations}/{len(metrics)} scale violations acceptable",
            "weight": 0.7,
            "attrs": {"total_violations": violations, "total_scales": len(metrics)},
        })
        f["edges"].append({"src": a_id, "dst": "C1", "rel": "supports", "weight": 0.7})
        f["morphs"].extend([
            {"op": "add_node", "node": {"id": a_id, "type": "Assumption"}},
            {"op": "add_edge", "src": a_id, "dst": "C1", "rel": "supports"},
        ])
    return f

def make_stitch(base_frame: dict, realized_move: float) -> dict:
    f = copy.deepcopy(base_frame)
    f["t_logical"] = 3
    evid = "E_outcome"
    f["nodes"].append({
        "id": evid,
        "type": "Evidence",
        "label": f"Realized outcome: {realized_move:+.2%}",
        "weight": 0.95,
        "attrs": {
            "realized_move": realized_move,
            "measurement_time": datetime.now(timezone.utc).isoformat(),
            "source": "market_data",
        },
    })
    f["edges"].append({"src": evid, "dst": "C1", "rel": "supports", "weight": 0.95})
    f["morphs"].extend([
        {"op": "add_node", "node": {"id": evid, "type": "Evidence"}},
        {"op": "add_edge", "src": evid, "dst": "C1", "rel": "supports"},
    ])
    return f

# ----------------------------
# Main
# ----------------------------
def main():
    ap = argparse.ArgumentParser(description="FlowState → OpenLine (v2-lite)")
    ap.add_argument("--url", default="http://127.0.0.1:8088/frame", help="OpenLine /frame URL")
    ap.add_argument("--stream-id", default="flowstate-v2-lite", help="Stream ID")
    ap.add_argument("--asset-class", default="equity",
                    choices=list(ASSET_THRESHOLDS.keys()), help="Asset class")
    ap.add_argument("--model", default="ibm-research/flowstate-r1", help="Model name")
    ap.add_argument("--scale-pair", action="append", help="Pair like 'min->hour' (repeatable)")
    ap.add_argument("--path-a", action="append", help="Path A (aggregate) array")
    ap.add_argument("--path-b", action="append", help="Path B (direct) array")
    ap.add_argument("--path-a-file", action="append", help="Path A file (CSV/JSON)")
    ap.add_argument("--path-b-file", action="append", help="Path B file (CSV/JSON)")
    ap.add_argument("--realized-move", type=float, help="Outcome percent move, e.g. 0.012")
    ap.add_argument("--dry-run", action="store_true", help="Print frames, don’t POST")
    args = ap.parse_args()

    # Build scale data map
    scale_data: Dict[str, Dict[str, List[float]]] = {}
    if args.scale_pair and args.path_a and args.path_b:
        for i, pair in enumerate(args.scale_pair):
            if i < len(args.path_a) and i < len(args.path_b):
                scale_data[pair] = {
                    "path_a": parse_array(args.path_a[i]),
                    "path_b": parse_array(args.path_b[i]),
                }
    if args.scale_pair and args.path_a_file and args.path_b_file:
        for i, pair in enumerate(args.scale_pair):
            if i < len(args.path_a_file) and i < len(args.path_b_file):
                scale_data[pair] = {
                    "path_a": load_series(args.path_a_file[i]),
                    "path_b": load_series(args.path_b_file[i]),
                }
    if not scale_data:
        # Demo data
        scale_data = {
            "min->hour": {
                "path_a": [100.0, 101.5, 99.8, 102.1, 101.2],
                "path_b": [100.0, 101.2, 100.1, 101.8, 101.0],
            },
            "hour->day": {
                "path_a": [100.0, 101.0, 100.5, 101.8],
                "path_b": [100.0, 100.8, 100.7, 101.5],
            },
        }

    # Compute metrics per pair
    metrics: Dict[str, dict] = {}
    for pair, paths in scale_data.items():
        s_from, s_to = parse_pair(pair)
        ds, md, mr, n = delta_scale(paths["path_a"], paths["path_b"])
        thr = pick_threshold(args.asset_class, s_from, s_to)
        metrics[pair] = {
            "delta_scale": ds,
            "max_deviation": md,
            "mean_ratio": mr,
            "n_points": n,
            "threshold": thr,
        }

    # Report
    print(f"=== Multi-Scale Analysis ({args.asset_class}) ===")
    for pair, m in metrics.items():
        status = "PASS" if (m["n_points"] and m["delta_scale"] <= m["threshold"]) else "VIOLATION"
        print(f"{pair}: Δ_scale={m['delta_scale']:.4f} vs thr={m['threshold']:.4f}  {status}")

    # Frames
    sync = make_sync(args.stream_id, args.asset_class, args.model, metrics)
    measure = make_measure(sync, metrics)
    frames = [sync, measure]
    if args.realized_move is not None:
        frames.append(make_stitch(measure, args.realized_move))

    for i, frame in enumerate(frames, 1):
        kind = ["SYNC", "MEASURE", "STITCH"][i-1] if i <= 3 else f"FRAME_{i}"
        print(f"\n--- {kind} ---")
        if args.dry_run:
            print(json.dumps(frame, indent=2))
        else:
            r = httpx.post(args.url, json=frame, timeout=30)
            try:
                r.raise_for_status()
                print("OK:", r.json().get("digest", {}))
            except Exception as e:
                print("POST failed:", r.text)
                raise

if __name__ == "__main__":
    main()
