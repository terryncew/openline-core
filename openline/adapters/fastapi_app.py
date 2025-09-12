# openline/adapters/fastapi_app.py
from __future__ import annotations
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException
from openline.schema import Frame, BusReply, Digest
from openline.digest import compute_digest, holonomy_gap

app = FastAPI(title="OpenLine Bus", version="0.1.0")

_LAST_DIGEST: Dict[str, Digest] = {}  # per-stream cache

@app.post("/frame", response_model=BusReply)
def post_frame(frame: Frame) -> BusReply:
    # recompute digest (server is source of truth)
    d_now = compute_digest(frame.nodes, frame.edges)
    d_prev: Optional[Digest] = _LAST_DIGEST.get(frame.stream_id)

    # make guards here later if you want; for now just compute and return
    _LAST_DIGEST[frame.stream_id] = d_now

    # update telemetry with holonomy
    frame.telem.delta_hol = holonomy_gap(d_prev, d_now) if d_prev else 0.0

    return BusReply(ok=True, digest=d_now, telem=frame.telem)

def main() -> None:
    import uvicorn
    uvicorn.run("openline.adapters.fastapi_app:app", host="127.0.0.1", port=8088, reload=False)
