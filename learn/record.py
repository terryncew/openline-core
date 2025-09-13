# minimal JSONL logger for receipts → learning rows
import json, time
from pathlib import Path

DATA = Path("data"); DATA.mkdir(exist_ok=True)
LOG  = DATA / "receipts.jsonl"

def _safe_num(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def write_row(*, context, claim, so_conf,
              telem, counters, realized,
              asset="default", pair="",
              direction=None, target_ret=None):
    row = {
        "ts": int(time.time()),
        "asset": (asset or "default").lower(),
        "pair": pair or "",                 # e.g., "min→hour"
        "context": context or {},
        "claim": claim,
        "direction": (direction or None),   # "up" | "down" | None
        "target_ret": target_ret,           # e.g., 0.003 for +0.3%
        "so_conf": _safe_num(so_conf, None),
        "delta_scale": _safe_num((telem or {}).get("delta_scale"), None),
        "counters": list(counters or []),
        "realized": realized or {},         # {"ret": 0.005, "hit": True} OK
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
