from __future__ import annotations

import os
import json
import time
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from openline.schema import Frame, BusReply, Digest
from openline.digest import compute_digest, holonomy_gap
from openline.guards import guard_check

app = FastAPI(title="OpenLine Bus", version="0.1.0")

# CORS so the client or a web page can hit it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# demo in-memory digest store (by stream)
_LAST_DIGEST: Dict[str, Digest] = {}

@app.get("/health")
def health():
    return {"ok": True, "ts": int(time.time())}

@app.post("/frame", response_model=BusReply)
async def post_frame(request: Request) -> BusReply:
    """
    Accept either {"frame": {...}} or raw {...}.
    Recompute digest, run guards, update Δ_hol, return BusReply.
    """
    payload = await request.json()
    if isinstance(payload, dict) and "frame" in payload:
        payload = payload["frame"]

    try:
        frame = Frame(**payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bad frame: {e}")

    # recompute digest on the bus
    d_now = compute_digest(frame.nodes, frame.edges)
    d_prev: Optional[Digest] = _LAST_DIGEST.get(frame.stream_id)

    # ensure guards see recomputed values
    frame.digest = d_now

    try:
        guard_check(frame, prev_digest=d_prev)
    except ValueError as e:
        # schema/guard violation → 422
        raise HTTPException(status_code=422, detail=str(e)) from e

    # commit latest digest
    _LAST_DIGEST[frame.stream_id] = d_now

    # update telem with holonomy gap
    frame.telem.delta_hol = holonomy_gap(d_prev, d_now) if d_prev else 0.0

    return BusReply(ok=True, digest=d_now, telem=frame.telem)

def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")  # 0.0.0.0 works in Codespaces
    uvicorn.run("openline.adapters.fastapi_app:app", host=host, port=port, reload=False)
