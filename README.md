[![OpenLine-compatible](https://img.shields.io/badge/OpenLine-compatible-v0.1-1f6feb)](https://github.com/terryncew/openline-core)
![Schema check](https://github.com/terryncew/openline-core/actions/workflows/validate.yml/badge.svg?branch=main)
![OLP wire v0.1](https://img.shields.io/badge/OLP%20wire-v0.1-1f6feb?style=flat-square)
[![Docs](https://img.shields.io/website?url=https%3A%2F%2Fterryncew.github.io%2Fopenline-core%2F&label=Docs%20(Pages))](https://terryncew.github.io/openline-core/)
![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=flat-square)
# Open Line Protocol (OLP)

AI agents speaking geometry, not paragraphs.

OLP sends small graphs (the **shape**) plus smooth updates (the **liquid**). That makes plans auditable, merges conflict-aware, and changes explicit.

**You get:**

- **Frozen wire** (v0.1): typed schema you can depend on
- **Guards**: stop self-licking loops, silent deletions, order-debt spikes
- **Digest**: 5-number “shape fingerprint” (+ Δ_hol holonomy gap)
- **Telemetry**: coherence, curvature, commutator—so agents auto-throttle
- **One-command demo**: up in seconds; extend in minutes

-----

### Hello Frame (curl)

```bash
curl -s -X POST http://127.0.0.1:8088/frame \
  -H 'Content-Type: application/json' -d '{
  "stream_id": "demo-1",
  "t_logical": 1,
  "gauge": "sym",
  "units": "confidence:0..1,cost:tokens",
  "nodes": [
    {"id":"C1","type":"Claim","label":"Bullets silence","weight":0.78},
    {"id":"E1","type":"Evidence","label":"No motive yet","weight":0.90}
  ],
  "edges": [{"src":"E1","dst":"C1","rel":"supports","weight":0.90}],
  "digest": {"b0":1,"cycle_plus":0,"x_frontier":0,"s_over_c":1.0,"depth":0},
  "morphs": [],
  "telem": {"phi_sem":0.72,"phi_topo":0.66,"delta_hol":0.0,"kappa_eff":0.30,
            "commutator":0.0,"cost_tokens":0,"da_drift":0.0},
  "signature": null
}'
```

-----

## What’s on the wire (v0.1)

- **Nodes**: `Claim | Evidence | Counter | Assumption | Constraint | PlanStep | Outcome | Principle | Motif`
- **Edges**: `supports | contradicts | depends_on | derives | updates | instantiates | illustrates`
- **Digest** (5-number fingerprint):
  - **b₀** (components) • **cycle_plus** (support cycles) • **x_frontier** (live contradictions)
  - **s_over_c** (support:contradiction) • **depth** (longest dependency chain)
- **Holonomy gap**: `Δ_hol = ||digest_post − digest_pre||₁` (order-debt across a loop)
- **Morphs**: `add_* | del_* | retype | reweight | merge | split | homotopy` (operation-based CRDT)
- **Telemetry**: `phi_sem, phi_topo, delta_hol, kappa_eff, commutator, cost_tokens, da_drift`

-----

## Guardrails (server rejects if)

1. **cycle_plus > cap** (default 4)
1. **x_frontier drops by deletion only** (must resolve via Assumption/Counter)
1. **Δ_hol spikes without explanatory node** (measured on a bent prior)

These prevent self-reinforcing myths, silent objection erasure, and “too-clean” rewrites.

-----

## Stitch in three beats

**SYNC** (prior skeleton) → **MEASURE** (probe morphs) → **STITCH** (commit or targeted counter-morph).

Different models, same invariants. Coord-free, conflict-aware collaboration.

-----

## Local dev & testing

```bash
# Install dependencies and run demo
uv sync && uv run examples/quickstart.py

# Run server alone  
uv run uvicorn openline.adapters.fastapi_app:app --port 8088

# Send frames from another shell
uv run examples/demo_client.py
```

**Run tests & checks:**

```bash
uv run ruff check .
uv run mypy openline  
uv run pytest -q --cov=openline
```

-----

## Repo layout

```
openline/
├── README.md
├── pyproject.toml
├── openline/
│   ├── schema.py         # OLP v0.1 Pydantic models (frozen wire)
│   ├── digest.py         # 5-number digest + Δ_hol
│   ├── guards.py         # guard checks
│   ├── telem.py          # coherence/curvature calculators
│   ├── crypto.py         # witness marks (Merkle/sign)
│   └── adapters/
│       ├── fastapi_app.py      # HTTP bus
│       └── stitch_bridge.py    # Stitch Scheduler → Frame mapping
├── examples/
│   ├── quickstart.py     # one-command demo
│   └── demo_client.py    # SYNC→MEASURE→STITCH sample
└── tests/
    ├── test_digest.py
    ├── test_guards.py
    └── test_wire.py
```

-----

## Design principles

**Ship-grade fundamentals:**

1. **One-command magic**: demo runs in a single line
1. **Frozen wire**: OLP v0.1 is versioned and backward-compatible
1. **Small, sharp core**: protocol, digest, guards, bus. Everything else plugs in
1. **Observability baked-in**: structured logs + OTel hooks
1. **Production hygiene**: types, lint, tests, coverage gates in CI
1. **Explicit failure modes**: actionable guard errors, no silent corruption

-----

## API surface

```
POST /frame    # Submit a Frame
→ {ok, digest, telem} or HTTP 422 with guard error
```

The demo server recomputes digests and validates guards. Your client can send its local digest, but the bus is the source of truth.

-----

## Roadmap

- WebSocket broadcast & stream replay
- Queue/Store adapters (SQS/Kafka, Postgres, S3)
- Determinism Anchor probe (batch-invariance check)
- Topological coherence scorer plugin (β₀/β₁ via lightweight persistence)
- Witness marks (Merkle proofs + signatures) on frames
- Multi-frame Stitch examples (RAG planning, tool chains)

-----

## Contributing

We love small, sharp PRs.

- If you touch `openline/schema.py`, include migration note + tests
- Keep core coverage ≥ 90% (`pytest --cov`)
- Run `ruff` and `mypy` before pushing
- Add rationale to PR; update examples/docs if behavior changes

See `CONTRIBUTING.md` for the full checklist.

-----

## Security

Report vulnerabilities via GitHub’s private reporting (**Security** → **Report a vulnerability**).  
**Planned:** signed releases & checksums (see `SECURITY.md`).

-----

## License

MIT (see `LICENSE`). Do what you want, credit the project, no warranties.

-----

## Appendix: The 5-number digest

- **b₀** — are we one connected argument or many islands?
- **cycle_plus** — are we starting to “prove ourselves with ourselves”?
- **x_frontier** — how many live contradictions remain?
- **s_over_c** — is support outrunning contradiction?
- **depth** — how deep is the dependency chain (fragility risk)?

Keep `Δ_hol` small between SYNC and STITCH, and your agents won’t “clean up” truth by deleting objections—they’ll resolve them on the record.

-----

**OpenLine lets agents speak geometry.**  
Copy the demo, shape your first Frame, and ship.

-----

## 🚀 Quickstart

### Option 1: Run in GitHub Codespaces
1. Click the green **Code** button → **Create codespace**.
2. In the terminal:
   ```bash
   uv sync --extra server
   uv run olp-server

	3.	Open a second terminal:

python examples/send_frame.py



Option 2: Run locally
	1.	Install uv.
	2.	Clone the repo:

git clone https://github.com/terryncew/openline-core.git
cd openline-core


	3.	Install + run:

uv sync --extra server
uv run olp-server


	4.	In another terminal:

python examples/send_frame.py



You should see a JSON reply with ok: true and a digest.

cff-version: 1.2.0
title: Open Line Protocol (OLP)
message: Cite this software if you use OLP.
authors: [{ family-names: White, given-names: Terrynce }]
version: 0.1.0
url: https://github.com/terryncew/openline-core

