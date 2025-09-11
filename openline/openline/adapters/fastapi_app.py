from __future__ import annotations

from typing import Dict, Optional
from fastapi import FastAPI, HTTPException

from openline.schema import Frame, BusReply, Digest
from openline.digest import compute_digest, holonomy_gap   # your helpers
from openline.guards import guard_check                    # your guards

# ----------------------------------------
# FastAPI app
# ----------------------------------------
app = FastAPI(title="OpenLine Bus", version="0.1.0")

# Last digest per stream (in-memory demo store)
_LAST_DIGEST: Dict[str, Digest] = {}

@app.post("/frame", response_model=BusReply)
def post_frame(frame: Frame) -> BusReply:
    """
    Accept a Frame, recompute digest (bus = source of truth),
    run guards, update Δ_hol, and return BusReply.
    """
    # Recompute digest
    d_now = compute_digest(frame.nodes, frame.edges)
    d_prev: Optional[Digest] = _LAST_DIGEST.get(frame.stream_id)

    # Make sure guards see the recomputed values
    frame.digest = d_now

    # Guard checks → 422 on violation
    try:
        guard_check(frame, prev_digest=d_prev)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Commit latest digest for this stream
    _LAST_DIGEST[frame.stream_id] = d_now

    # Update telemetry with holonomy gap computed on the bus
    frame.telem.delta_hol = holonomy_gap(d_prev, d_now) if d_prev else 0.0

    return BusReply(ok=True, digest=d_now, telem=frame.telem)

def main() -> None:
    """Entry point for `olp-server`."""
    import uvicorn
    uvicorn.run("openline.adapters.fastapi_app:app",
                host="127.0.0.1", port=8088, reload=False)
