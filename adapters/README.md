# OpenLine Adapters — from text to frame

Adapters turn raw LLM output into an OLP frame: a compact graph of claims, evidence, and counters with a 5-number digest. [COLE](https://github.com/terryncew/COLE-Coherence-Layer-Engine-) then measures it. This directory hosts reference adapters and the adapter API.

## Why frames?

Plain text hides structure. Frames make it auditable:

- What was **claimed**?
- What **supported** it?
- What **contradicted** it?
- Did the reasoning **loop**?
- How **stressed** was the run?

-----

## The OLP Frame (wire format)

```json
{
  "olp_version": "0.1",
  "frame_id": "auto",
  "agent": { "id": "agent-1", "model": "gpt-4o-mini" },

  "graph": {
    "nodes": [
      { "id": "c1", "type": "claim",   "text": "X causes Y" },
      { "id": "e1", "type": "evidence","text": "Study A (2023)" },
      { "id": "k1", "type": "counter", "text": "Z moderates the effect" }
    ],
    "edges": [
      { "src": "e1", "dst": "c1", "rel": "supports" },
      { "src": "k1", "dst": "c1", "rel": "counters" }
    ]
  },

  "digest": {
    "len": 812,          // token length
    "uniq": 0.81,        // type-token ratio or similar uniqueness proxy
    "loops": 0,          // detected cycle count
    "contrad": 1,        // contradiction count
    "hash": "sha256:…"   // stable content hash
  },

  "telem": {
    "phi_topo": 0.79,        // optional: topological quality proxy
    "phi_sem_proxy": 0.61    // optional: semantic quality proxy
  }
}
```

**Minimal contract:** `graph.nodes`, `graph.edges`, and `digest.*` must exist. Everything else is optional but recommended.

-----

## Adapter API (reference)

**Goal:** take `(text, context) → return a valid Frame`

```python
# adapters/frames/text_adapter.py
from openline.schema import Frame
from openline.digest import compute_digest
from openline.extract import find_claims, find_evidence, find_counters, build_edges

def to_frame(text: str, *, model="unknown", ctx=None) -> Frame:
    claims   = find_claims(text)     # list[str]
    evidence = find_evidence(text)   # list[str]
    counters = find_counters(text)   # list[str]

    nodes = []
    for i, t in enumerate(claims):   nodes.append({"id": f"c{i}", "type":"claim", "text": t})
    for i, t in enumerate(evidence): nodes.append({"id": f"e{i}", "type":"evidence", "text": t})
    for i, t in enumerate(counters): nodes.append({"id": f"k{i}", "type":"counter", "text": t})

    edges = build_edges(nodes)       # heuristics: supports/counters by proximity & cues

    digest = compute_digest(text=text, nodes=nodes, edges=edges)
    return {
        "olp_version": "0.1",
        "frame_id": "auto",
        "agent": { "id": "agent-1", "model": model },
        "graph": { "nodes": nodes, "edges": edges },
        "digest": digest
    }
```

### Heuristics that work surprisingly well (start simple):

- **Claims:** assertive sentences (“is”, “will”, “therefore”, conclusions)
- **Evidence:** citations, numbers, “according to…”, URLs, datasets
- **Counters:** “however”, “but”, “fails when…”, rival results
- **Edges:** `supports` when evidence is adjacent and referential; `counters` when prefixed by concession/negation

-----

## Contract Tests (don’t ship without them)

```python
def test_minimal_contract():
    f = to_frame("X causes Y. According to Smith 2023… However Z…")
    assert "graph" in f and "nodes" in f["graph"] and "edges" in f["graph"]
    d = f["digest"]; assert all(k in d for k in ["len","uniq","loops","contrad","hash"])
    assert any(n["type"]=="claim" for n in f["graph"]["nodes"])
```

-----

## Using adapters with COLE

### Library

```python
from adapters.frames.text_adapter import to_frame
from cole import compute_metrics, write_receipt

frame = to_frame(raw_llm_text, model="claude-3.7")
metrics, status = compute_metrics(frame)
write_receipt(frame, metrics, out="docs/receipt.latest.json")
```

### HTTP (if you run the tiny hub)

```bash
# POST a built frame
curl -X POST http://localhost:8088/frame \
  -H 'Content-Type: application/json' \
  -d @frame.json
```

-----

## Quality knobs (where to tune)

- **Loops:** simple cycle detection over `graph.edges`; count >0 often predicts drift
- **Contradictions:** sentence-level negation against earlier claims
- **uniq:** type-token ratio capped to [0,1]—too low ⇒ boilerplate; too high ⇒ ramble
- **φ proxies:** start with degree/assortativity (topo), lexical entailment score (semantic)

-----

## What “good” looks like

- Small, connected graph with at least one claim and one supporting edge
- Digest present and stable across whitespace/no-op edits
- κ stays green/amber on routine answers; goes red on long, contradictory rambles

-----

## Contributing

- Keep adapters small and pure
- Don’t break the frame contract; add fields under `telem` if needed
- Provide a fixture (`tests/fixtures/*.txt` → `*.frame.json`) and a contract test

-----

## License

Same as repo root. Adapters are reference implementations—use, fork, or replace.
