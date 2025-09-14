# openline/adapters/fastapi_app.py
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json, time, uuid

app = FastAPI(title="OpenLine /frame shim")

# wide-open CORS so your client and card can hit it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

FRAMES_LOG = Path("data/frames.log")
FRAMES_LOG.parent.mkdir(parents=True, exist_ok=True)

def _json(data: dict) -> Response:
    return Response(
        content=json.dumps(data),
        media_type="application/json",
        headers={"Cache-Control": "no-store"}  # always fresh for the card
    )

@app.get("/health")
def health():
    return _json({"ok": True, "time": int(time.time())})

@app.post("/frame")
async def post_frame(req: Request):
    # ~250 KB guard so a bad client can't wedge the server
    raw = await req.body()
    if raw and len(raw) > 256_000:
        return _json({"ok": False, "error": "payload too large"})

    # accept either {"frame": {...}} or raw {...}
    try:
        body = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw or b"{}")
    except Exception:
        body = {}

    frame = body.get("frame", body) or {}

    # normalize to the bits we actually care about (keeps digest if present)
    nodes  = frame.get("nodes")  or []
    edges  = frame.get("edges")  or []
    morphs = frame.get("morphs") or []
    telem  = frame.get("telem")  or {}
    norm   = {"nodes": nodes, "edges": edges, "morphs": morphs, "telem": telem}
    if "digest" in frame:
        norm["digest"] = frame["digest"]

    # append to a simple log (one line per frame)
    fid = str(uuid.uuid4())
    try:
        FRAMES_LOG.write_text(FRAMES_LOG.read_text() + json.dumps({
            "t": int(time.time()), "id": fid, "frame": norm
        }) + "\n", encoding="utf-8") if FRAMES_LOG.exists() else FRAMES_LOG.write_text(
            json.dumps({"t": int(time.time()), "id": fid, "frame": norm}) + "\n", encoding="utf-8"
        )
    except Exception:
        pass  # logging must never break the endpoint

    return _json({
        "ok": True, "accepted": True, "id": fid,
        "telem": telem, "counts": {"nodes": len(nodes), "edges": len(edges)}
    })
