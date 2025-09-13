# rolls through receipts.jsonl → writes data/params.json with
# - calibration table for "So:" confidence
# - tuned Δ_scale caps per asset×pair (80th pct of hits)
import json, time, argparse, tempfile, os
from pathlib import Path

DATA = Path("data"); DATA.mkdir(exist_ok=True)
IN   = DATA / "receipts.jsonl"
OUT  = DATA / "params.json"

def load_rows():
    if not IN.exists(): return
    for line in IN.open():
        y = json.loads(line)
        rz = y.get("realized", {}) or {}
        if "hit" not in rz:
            ret = rz.get("ret")
            dirn = (y.get("direction") or "").lower()
            thr  = y.get("target_ret")
            if isinstance(ret, (int, float)):
                if dirn == "up":     rz["hit"] = (ret >= (thr if isinstance(thr,(int,float)) else 0))
                elif dirn == "down": rz["hit"] = (ret <= (-(thr if isinstance(thr,(int,float)) else 0)))
                else: rz["hit"] = None
            else:
                rz["hit"] = None
            y["realized"] = rz
        yield y

def percentile(xs, q):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs)-1)*q
    f = int(k); c = min(f+1, len(xs)-1)
    return xs[f] + (xs[c]-xs[f])*(k-f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lookback-days", type=int, default=30)
    args = ap.parse_args()
    cutoff = time.time() - args.lookback_days*86400

    rows = [r for r in load_rows() if r.get("ts", 0) >= cutoff]

    # tuned caps per asset×pair (80th percentile of Δ among hits)
    caps = {}
    by_key = {}
    for r in rows:
        key = (r.get("asset","default"), r.get("pair",""))
        by_key.setdefault(key, []).append(r)
    for (asset, pair), rr in by_key.items():
        hits = [r for r in rr if isinstance(r.get("delta_scale"), (int,float)) and r.get("realized",{}).get("hit") is True]
        ds_vals = [float(r["delta_scale"]) for r in hits]
        cap = percentile(ds_vals, 0.80)
        if cap is not None:
            caps.setdefault(asset, {})[pair] = round(max(1e-3, cap), 3)

    # simple reliability table for "So:" (10 buckets, needs ≥50 per bucket)
    bins = [(i/10, (i+1)/10) for i in range(10)]
    cal  = {}
    for lo, hi in bins:
        b = [r for r in rows if isinstance(r.get("so_conf"), (int,float)) and lo <= r["so_conf"] < hi]
        if len(b) >= 50:
            hits = sum(1 for r in b if r.get("realized",{}).get("hit") is True)
            cal[f"{lo:.1f}-{hi:.1f}"] = round(hits / len(b), 3)

    # atomic write
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=str(DATA), encoding="utf-8")
    json.dump({"calibration": cal, "scale_caps": caps}, tmp, indent=2)
    tmp.flush(); os.fsync(tmp.fileno()); tmp.close()
    os.replace(tmp.name, OUT)
    print(f"Wrote {OUT} (rows={len(rows)}, keys={len(by_key)})")

if __name__ == "__main__":
    main()
