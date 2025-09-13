# scripts/test_tuned_cap.py
# Verifies the tuned-cap override in openline/guards.py

from pathlib import Path
import json

# Import your guard + default cap
from openline.guards import guard_check, DELTA_SCALE_CAP_DEFAULT

def try_case(ds, explained=False, label=""):
    """Run one guard_check case and print PASS/RAISE"""
    frame = {
        "telem": {"delta_scale": ds},
        "nodes": [
            {"type": "Claim", "attrs": {"asset_class": "equity", "cadence_pair": "min↔hour"}}
        ],
    }
    if explained:
        frame["nodes"].append({"type": "Counter", "label": "explanation"})
    try:
        guard_check(frame)
        print(f"[OK]     ds={ds:0.3f} {label}")
    except Exception as e:
        print(f"[RAISE]  ds={ds:0.3f} -> {e}")

def write_params(cap=0.020):
    """Create data/params.json with a tuned cap for equity/min↔hour"""
    Path("data").mkdir(exist_ok=True)
    payload = {"scale_caps": {"equity": {"min↔hour": cap}}, "calibration": {}}
    Path("data/params.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[setup] wrote data/params.json with tuned cap={cap:.3f} for equity/min↔hour")

def remove_params():
    p = Path("data/params.json")
    if p.exists():
        p.unlink()
        print("[setup] removed data/params.json (fallback to default caps)")

def main():
    # --- Tests using tuned cap (0.020) ---
    write_params(cap=0.020)
    try_case(0.028, label="(over tuned cap → should RAISE)")
    try_case(0.010, label="(under tuned cap → should PASS)")
    try_case(0.150, explained=True, label="(over tuned cap but explained → should PASS)")

    # --- Tests using default cap (no params.json) ---
    remove_params()
    default_cap = float(DELTA_SCALE_CAP_DEFAULT)
    try_case(default_cap - 0.005, label=f"(under default cap {default_cap:.3f} → should PASS)")
    try_case(default_cap + 0.050, label=f"(well over default cap {default_cap:.3f} → should RAISE)")

if __name__ == "__main__":
    main()
