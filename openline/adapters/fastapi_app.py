# openline/adapters/fastapi_app.py
from __future__ import annotations

from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Reuse your existing guard
from openline.guards import guard_check

app = FastAPI(title="OpenLine OLP bridge")

# open CORS so your sidecar / emitter can post from anywhere in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/frame")
async def post_frame(req: Request):
    # 1) parse JSON safely
    try:
        payload: Dict[str, Any] = await req.json()
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"bad json: {e}"}, status_code=400)

    # 2) be tolerant about missing keys
    payload.setdefault("nodes", [])
    payload.setdefault("edges", [])
    payload.setdefault("morphs", [])
    payload.setdefault("telem", {})
    payload.setdefault("digest", None)
    payload.setdefault("stream_id", payload.get("stream", "stack"))

    # 3) run delta-scale guard (and any others you added)
    try:
        guard_check(payload)
    except Exception as e:
        # return a clean validation-ish error instead of a 500
        return JSONResponse({"ok": False, "error": str(e)}, status_code=422)

    # 4) minimal success echo; you can expand later
    return {
        "ok": True,
        "accepted": True,
        "telem": payload.get("telem", {}),
        "stream_id": payload.get("stream_id"),
    }
