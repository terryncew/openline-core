# scripts/ingest_frame.py
# Merge OpenLine frame → COLE receipt.latest.json (v0.2 signals)
from __future__ import annotations
import json, os
from pathlib import Path

REC = Path("docs/receipt.latest.json")
FRAME_CAND = [
    Path("artifacts/frame.json"),
    Path("docs/frame.json"),
    Path(os.getenv("OLP_FRAME_JSON",""))
]

def _load(p: Path):
    try: return json.loads(p.read_text("utf-8"))
    except Exception: return None

def main():
    frame=None
    for p in FRAME_CAND:
        if isinstance(p, Path) and p.is_file():
            frame=_load(p); 
            if frame: break
    if not frame:
        print("[info] no OLP frame found"); return

    tel = frame.get("telem", {})
    dig = frame.get("digest", {})
    j = _load(REC) or {}

    j.setdefault("temporal", {}).setdefault("latest", {})
    j["temporal"]["latest"]["kappa"]     = float(tel.get("kappa_eff", 0.0))
    j["temporal"]["latest"]["delta_hol"] = float(tel.get("delta_hol", 0.0))
    j["temporal"]["latest"]["jsd"]       = None  # slot reserved (v0.2)
    j.setdefault("narrative", {}).setdefault("continuity", {})
    j["narrative"]["continuity"]["cycles_C"]        = int(dig.get("cycle_plus", 0))
    j["narrative"]["continuity"]["contradictions_X"]= int(dig.get("x_frontier", 0))

    REC.write_text(json.dumps(j, indent=2), encoding="utf-8")
    print(f"[ok] receipt.temporal.latest.kappa={j['temporal']['latest']['kappa']:.3f} Δhol={j['temporal']['latest']['delta_hol']:.3f} C={j['narrative']['continuity']['cycles_C']} X={j['narrative']['continuity']['contradictions_X']}")

if __name__=="__main__":
    main()
