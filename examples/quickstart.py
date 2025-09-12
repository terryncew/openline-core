import time, copy
import httpx

BASE = "http://127.0.0.1:8088/frame"

def post(frame):
    r = httpx.post(BASE, json=frame, timeout=10)
    print(r.status_code, r.json())

f1 = {
    "stream_id": "demo-1", "t_logical": 1, "gauge": "sym",
    "units": "confidence:0..1,cost:tokens",
    "nodes": [
        {"id": "C1", "type": "Claim", "label": "Bullets silence", "weight": 0.78},
        {"id": "E1", "type": "Evidence", "label": "No motive yet", "weight": 0.90},
    ],
    "edges": [{"src": "E1", "dst": "C1", "rel": "supports", "weight": 0.90
