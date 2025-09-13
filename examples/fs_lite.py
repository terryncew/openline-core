#!/usr/bin/env python3
# fs_lite.py — FlowState → OpenLine mini demo (SYNC → MEASURE → STITCH)
# No schema changes. Everything extra lives in node.attrs.

import json, argparse, time
from datetime import datetime, timezone
from urllib import request, error

URL_DEFAULT = "http://127.0.0.1:8088/frame"

def post(url, obj):
    data = json.dumps(obj).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type":"application/json"})
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(body)
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def mk_frame(stream_id, t_logical, nodes, edges, morphs, telem_extra=None):
    telem = {
        "phi_sem": 0.72, "phi_topo": 0.66, "delta_hol": 0.0,
        "kappa_eff": 0.30, "commutator": 0.0, "cost_tokens": 0, "da_drift": 0.0
    }
    if telem_extra:
        telem.update(telem_extra)
    return {
        "stream_id": stream_id,
        "t_logical": t_logical,
        "gauge": "sym",
        "units": "confidence:0..1,cost:tokens",
        "nodes": nodes,
        "edges": edges,
        "digest": {"b0": 0, "cycle_plus": 0, "x_frontier": 0, "s_over_c": 0.0, "depth": 0},
        "morphs": morphs,
        "telem": telem,
        "signature": None
    }

def delta_scale(path_a, path_b):
    # mean(|A-B|) / mean(|B|)
    if not path_a or not path_b or len(path_a) != len(path_b):
        return 0.0
    diffs = [abs(a-b) for a,b in zip(path_a, path_b)]
    mean_abs_b = sum(abs(b) for b in path_b)/len(path_b) or 1e-8
    return (sum(diffs)/len(diffs))/mean_abs_b

def main():
    ap = argparse.ArgumentParser(description="FlowState → OLP mini receipt (fs_lite)")
    ap.add_argument("--url", default=URL_DEFAULT, help="OLP endpoint")
    ap.add_argument("--stream", default="flowstate-demo-1", help="stream id")
    ap.add_argument("--cad", default="day", help="cadence label, e.g. day")
    ap.add_argument("--model", default="ibm-research/flowstate-r1", help="model name")
    ap.add_argument("--realized", type=float, default=None, help="optional realized move (e.g. 0.005)")
    args = ap.parse_args()

    # Demo data (minute→hour consistency check)
    # Path A: min→aggregate→hour ; Path B: direct hour decode
    A = [100.0, 100.8, 101.1, 100.6]
    B = [100.0, 100.7, 101.0, 100.5]
    dsc = round(delta_scale(A, B), 4)  # e.g. 0.0028 = 0.28%

    # ---------- SYNC ----------
    nodes = [
        {"id":"C1","type":"Claim",
         "label":"FlowState predicts SPY close ↑ +0.6% tomorrow",
         "weight":0.78,
         "attrs":{
            "cadence": args.cad,
            "horizon": "1d",
            "t0": now_iso(),
            "model": args.model,
            "decode_basis": "FBD:K=64",
            "context_span": "30d@min"
         }},
        {"id":"E1","type":"Evidence",
         "label":"Context: last 30d minute bars",
         "weight":0.9,
         "attrs":{"context_span":"30d@min"}},
        {"id":"E2","type":"Evidence",
         "label":"Backtest metrics",
         "weight":0.8,
         "attrs":{"metric":"sMAPE@hour=0.081; sMAPE@day=0.052"}}
    ]
    edges = [
        {"src":"E1","dst":"C1","rel":"supports","weight":0.9},
        {"src":"E2","dst":"C1","rel":"supports","weight":0.8}
    ]
    f1 = mk_frame(args.stream, 1, nodes, edges, [], {"delta_scale": 0.0})
    code, body = post(args.url, f1)
    print(f"[SYNC] {code} -> {body}")

    # ---------- MEASURE ----------
    # Treat >3% as a drift violation (demo threshold).
    morphs = []
    nodes2 = [{"id":"C1","type":"Claim"}]  # keep the original id around
    edges2 = []
    telem2 = {"delta_scale": dsc}
    if dsc > 0.03:
        nodes2 += [
            {"id":"X1","type":"Counter",
             "label":f"Scale drift min→hour Δ_scale={dsc:.3%}",
             "weight":0.8,
             "attrs":{"scale_pair":"min→hour","delta_scale":dsc}},
            {"id":"A1","type":"Assumption",
             "label":"Tolerance: Δ_scale ≤ 3% during transition",
             "weight":0.7}
        ]
        edges2 += [
            {"src":"X1","dst":"C1","rel":"contradicts","weight":0.8},
            {"src":"A1","dst":"C1","rel":"supports","weight":0.7}
        ]
        morphs += [
            {"op":"add_node","node":{"id":"X1","type":"Counter"}},
            {"op":"add_node","node":{"id":"A1","type":"Assumption"}},
            {"op":"add_edge","src":"X1","dst":"C1","rel":"contradicts"},
            {"op":"add_edge","src":"A1","dst":"C1","rel":"supports"}
        ]
    f2 = mk_frame(args.stream, 2, nodes2, edges2, morphs, telem2)
    code, body = post(args.url, f2)
    print(f"[MEASURE] {code} -> {body}")

    # ---------- STITCH (optional realized outcome) ----------
    if args.realized is not None:
        nodes3 = [{"id":"C1","type":"Claim"},
                  {"id":"E3","type":"Evidence",
                   "label":f"Realized close {args.realized:+.2%}",
                   "weight":0.95,
                   "attrs":{"cadence":"day","source":"exchange"}}]
        edges3 = [{"src":"E3","dst":"C1","rel":"supports","weight":0.95}]
        morphs3 = [
            {"op":"add_node","node":{"id":"E3","type":"Evidence"}},
            {"op":"add_edge","src":"E3","dst":"C1","rel":"supports"}
        ]
        f3 = mk_frame(args.stream, 3, nodes3, edges3, morphs3, {"delta_scale": max(0.0, dsc*0.3)})
        code, body = post(args.url, f3)
        print(f"[STITCH] {code} -> {body}")

if __name__ == "__main__":
    main()
