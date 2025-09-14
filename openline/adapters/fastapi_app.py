from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json, time, uuid

app = FastAPI(title="OpenLine OLP shim")

# permissive CORS (demo-friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

FRAMES_LOG = Path("data/frames.log")
FRAMES_LOG.parent.mkdir(parents=True, exist_ok=True)

@app.get("/health")
async def health():
    return {"ok": True, "ts": int(time.time())}

@app.post("/frame")
async def post_frame(req: Request):
    """
    Accepts either {"frame": {...}} or raw {...}. Never 500s.
    Logs a normalized frame and ACKs.
    """
    raw = await req.body()
    if len(raw) > 256_000:
        return JSONResponse({"ok": False, "error": "payload too large"}, status_code=413)
    try:
        body = json.loads(raw or b"{}")
    except Exception:
        body = {}
    frame = body.get("frame", body) if isinstance(body, dict) else {}
    nodes  = frame.get("nodes")  or []
    edges  = frame.get("edges")  or []
    morphs = frame.get("morphs") or []
    telem  = frame.get("telem")  or {}
    fid = str(uuid.uuid4())

    try:
        with FRAMES_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "id": fid, "frame": frame}) + "\n")
    except Exception:
        pass

    return {
        "ok": True, "accepted": True, "id": fid,
        "counts": {"nodes": len(nodes), "edges": len(edges), "morphs": len(morphs)},
        "telem": telem,
    }
