import httpx

URL = "http://127.0.0.1:8088/frame"

frame = {
    "stream_id": "demo-1",
    "t_logical": 1,
    "gauge": "sym",
    "units": "confidence:0..1,cost:tokens",
    "nodes": [
        {"id": "C1", "type": "Claim", "label": "Bullets silence", "weight": 0.78},
        {"id": "E1", "type": "Evidence", "label": "No motive yet", "weight": 0.90},
    ],
    "edges": [{"src": "E1", "dst": "C1", "rel": "supports", "weight": 0.90}],
    "digest": {"b0": 0, "cycle_plus": 0, "x_frontier": 0, "s_over_c": 0.0, "depth": 0},
    "morphs": [],
    "telem": {"phi_sem": 0.72, "phi_topo": 0.66, "delta_hol": 0.0,
              "kappa_eff": 0.30, "commutator": 0.0, "cost_tokens": 0, "da_drift": 0.0},
    "signature": None
}

def main() -> None:
    r = httpx.post(URL, json=frame, timeout=10)
    r.raise_for_status()
    print(r.json())

if __name__ == "__main__":
    main()
