# Open Line Protocol (OLP)

[![OpenLine-compatible](docs/badges/openline-compatible.svg)](https://github.com/terryncew/openline-core)
![Schema check](https://github.com/terryncew/openline-core/actions/workflows/validate.yml/badge.svg?branch=main)
![OLP wire v0.1](https://img.shields.io/badge/OLP%20wire-v0.1-1f6feb?style=flat-square)
[![Docs](https://img.shields.io/website?url=https%3A%2F%2Fterryncew.github.io%2Fopenline-core%2F&label=Docs%20(Pages))](https://terryncew.github.io/openline-core/)
![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=flat-square)

**AI agents speaking geometry, not paragraphs.**

OLP sends small graphs (the shape) plus smooth updates (the liquid). That makes plans auditable, merges conflict-aware, and changes explicit.

-----

## What You Get

- **Frozen wire (v0.1)** — Typed schema you can depend on
- **Guards** — Stop self-licking loops, silent deletions, order-debt spikes
- **Digest** — 5-number “shape fingerprint” + Δ_hol holonomy gap
- **Telemetry** — Coherence, curvature, commutator—so agents auto-throttle
- **One-command demo** — Up in seconds; extend in minutes

-----

## Quick Start

```bash
# Python 3.11+ and uv installed
uv sync && uv run examples/quickstart.py
```

**Server:** `http://127.0.0.1:8088/frame` (FastAPI)

Each posted Frame is re-digested and guard-checked.

> **Prereq (1 line):** `pip install uv`  ← installs Astral’s ultra-fast Python tool used in the quickstart.

### Troubleshooting (10-second fixes)
- **`uv: command not found`** → run `pip install uv`
- **Port 8088 already in use** → start on another port: `uv run olp-server --port 8090`
- **Client can’t reach the server** → make sure the server is running, or change the URL/port in your example client.

### Example Request

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

**Response:** `{ok: true, digest, telem}` or HTTP 422 with guard error

-----

## The Frame Schema

### Nodes

`Claim` | `Evidence` | `Counter` | `Assumption` | `Constraint` | `PlanStep` | `Outcome` | `Principle` | `Motif`

### Edges

`supports` | `contradicts` | `depends_on` | `derives` | `updates` | `instantiates` | `illustrates`

### Digest (5-number fingerprint)

- **b₀** (components) — Are we one connected argument or many islands?
- **cycle_plus** (support cycles) — Are we starting to “prove ourselves with ourselves”?
- **x_frontier** (live contradictions) — How many live contradictions remain?
- **s_over_c** (support:contradiction) — Is support outrunning contradiction?
- **depth** (longest dependency chain) — How deep is the dependency chain (fragility risk)?

### Holonomy Gap

**Δ_hol** = ||digest_post − digest_pre||₁ (order-debt across a loop)

### Telemetry

`phi_sem`, `phi_topo`, `delta_hol`, `kappa_eff`, `commutator`, `cost_tokens`, `da_drift`

-----

## Guards (what they prevent)

- **cycle_plus > cap** (default 4) — Self-reinforcing myths
- **x_frontier drops by deletion only** — Must resolve via Assumption/Counter; silent objection erasure
- **Δ_hol spikes without explanatory node** — “Too-clean” rewrites measured on a bent prior

These prevent self-reinforcing myths, silent objection erasure, and “too-clean” rewrites.

-----

## The Coordination Pattern

**SYNC** (prior skeleton) → **MEASURE** (probe morphs) → **STITCH** (commit or targeted counter-morph)

Different models, same invariants. Coord-free, conflict-aware collaboration.

-----

## Installation & Usage

### Run the demo

```bash
# Install dependencies and run demo
uv sync && uv run examples/quickstart.py

# Run server alone
uv run olp-server  # preferred (if entrypoint is defined)
# or
uv run uvicorn openline.adapters.fastapi_app:app --port 8088

# Send frames from another shell
uv run examples/demo_client.py
```

### Run tests & checks

```bash
uv run ruff check .
uv run mypy openline
uv run pytest -q --cov=openline
```

-----

## Project Structure

```
openline/
├── README.md
├── pyproject.toml
├── openline/
│   ├── schema.py           # OLP v0.1 Pydantic models (frozen wire)
│   ├── digest.py           # 5-number digest + Δ_hol
│   ├── guards.py           # guard checks
│   ├── telem.py            # coherence/curvature calculators
│   ├── crypto.py           # witness marks (Merkle/sign)
│   └── adapters/
│       ├── fastapi_app.py  # HTTP bus
│       └── stitch_bridge.py # Stitch Scheduler → Frame mapping
├── examples/
│   ├── quickstart.py       # one-command demo
│   └── demo_client.py      # SYNC→MEASURE→STITCH sample
└── tests/
    ├── test_digest.py
    ├── test_guards.py
    └── test_wire.py
```

-----

## Ship-grade fundamentals

- **One-command magic** — Demo runs in a single line
- **Frozen wire** — OLP v0.1 is versioned and backward-compatible
- **Small, sharp core** — Protocol, digest, guards, bus. Everything else plugs in
- **Observability baked-in** — Structured logs + OTel hooks
- **Production hygiene** — Types, lint, tests, coverage gates in CI
- **Explicit failure modes** — Actionable guard errors, no silent corruption

-----

## API

```
POST /frame  # Submit a Frame
→ {ok, digest, telem} or HTTP 422 with guard error
```

The demo server recomputes digests and validates guards. Your client can send its local digest, but the bus is the source of truth.

-----

## Roadmap

- [ ] WebSocket broadcast & stream replay
- [ ] Queue/Store adapters (SQS/Kafka, Postgres, S3)
- [ ] Determinism Anchor probe (batch-invariance check)
- [ ] Topological coherence scorer plugin (β₀/β₁ via lightweight persistence)
- [ ] Witness marks (Merkle proofs + signatures) on frames
- [ ] Multi-frame Stitch examples (RAG planning, tool chains)

-----

## Contributing

We love small, sharp PRs.

- If you touch `openline/schema.py`, include migration note + tests
- Keep core coverage ≥ 90% (`pytest --cov`)
- Run `ruff` and `mypy` before pushing
- Add rationale to PR; update examples/docs if behavior changes

See <CONTRIBUTING.md> for the full checklist.

-----

## Security

Report vulnerabilities via GitHub’s private reporting (Security → Report a vulnerability).

Planned: signed releases & checksums (see <SECURITY.md>).

-----

## License

MIT — see [LICENSE](./LICENSE). Do what you want, credit the project, no warranties.

-----

## Understanding the Digest

- **b₀** — are we one connected argument or many islands?
- **cycle_plus** — are we starting to “prove ourselves with ourselves”?
- **x_frontier** — how many live contradictions remain?
- **s_over_c** — is support outrunning contradiction?
- **depth** — how deep is the dependency chain (fragility risk)?

Keep `Δ_hol` small between SYNC and STITCH, and your agents won’t “clean up” truth by deleting objections—they’ll resolve them on the record.

-----

## Getting Started Fast

**Option 1: Codespaces**

1. Click the green Code button → Create codespace
1. In the terminal: `uv sync --extra server && uv run olp-server`
1. Open a second terminal: `python examples/send_frame.py`

**Option 2: Run locally**

1. Install [uv](https://github.com/astral-sh/uv)
1. Clone the repo:
   
   ```bash
   git clone https://github.com/terryncew/openline-core.git
   cd openline-core
   ```
1. Install + run:
   
   ```bash
   uv sync --extra server
   uv run olp-server
   ```
1. In another terminal: `python examples/send_frame.py`

You should see a JSON reply with `ok: true` and a digest.

-----

**OpenLine lets agents speak geometry.**

Copy the demo, shape your first Frame, and ship.

## Cite OpenLine Core

If you use OpenLine Core in academic or policy work, please cite:

**APA**
White, T. (2025). *OpenLine Core: A tiny protocol for auditable agent receipts*. GitHub. https://github.com/terryncew/openline-core

**BibTeX**
@software{White_OpenLine_Core_2025,
  author       = {Terrynce White},
  title        = {OpenLine Core: A tiny protocol for auditable agent receipts},
  year         = {2025},
  url          = {https://github.com/terryncew/openline-core},
  publisher    = {GitHub},
  version      = {latest},
  note         = {Accessed: {{\today}}}
}

**Plain text**
White, T. (2025). OpenLine Core: A tiny protocol for auditable agent receipts. GitHub. https://github.com/terryncew/openline-core
