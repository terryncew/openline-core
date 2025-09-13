# quick KPIs: n, median Δ, % over cap (if params present), Brier/ACE
import json, statistics as st
from pathlib import Path

DATA = Path("data")
LOG = DATA / "receipts.jsonl"
PARAMS = DATA / "params.json"

def main():
    rows = [json.loads(l) for l in LOG.open()] if LOG.exists() else []
    params = json.loads(PARAMS.read_text()) if PARAMS.exists() else {"scale_caps":{}}

    ds = [r.get("delta_scale") for r in rows if isinstance(r.get("delta_scale"), (int,float))]
    med_ds = round(st.median(ds), 3) if ds else None

    # % over learned cap
    over = 0; total = 0
    for r in rows:
        dsr = r.get("delta_scale")
        if not isinstance(dsr,(int,float)): continue
        cap = params.get("scale_caps",{}).get(r.get("asset","default"),{}).get(r.get("pair",""))
        if isinstance(cap,(int,float)):
            total += 1
            if dsr > cap: over += 1
    pct_over = round(100*over/total,1) if total else None

    # Brier + ACE on so_conf
    brier_list = []
    bins = {i:[] for i in range(10)}
    for r in rows:
        p = r.get("so_conf"); lab = r.get("realized",{}).get("hit")
        if isinstance(p,(int,float)) and isinstance(lab,bool):
            brier_list.append((p - (1.0 if lab else 0.0))**2)
            bins[min(9, int(p*10))].append((p, 1.0 if lab else 0.0))
    brier = round(sum(brier_list)/len(brier_list), 3) if brier_list else None
    # ACE
    n = sum(len(v) for v in bins.values())
    ace = 0.0
    for v in bins.values():
        if not v: continue
        phat = sum(p for p,_ in v)/len(v)
        yhat = sum(y for _,y in v)/len(v)
        ace += (len(v)/n) * abs(phat - yhat) if n else 0.0
    ace = round(ace, 3) if n else None

    print(json.dumps({
        "n": len(rows),
        "median_delta_scale": med_ds,
        "pct_over_cap": pct_over,
        "brier": brier,
        "ace": ace
    }, indent=2))

if __name__ == "__main__":
    main()
