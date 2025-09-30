# Open Line Protocol (OLP)

[![OpenLine-compatible](docs/badges/openline-compatible.svg)](https://github.com/terryncew/openline-core)
![Schema check](https://github.com/terryncew/openline-core/actions/workflows/validate.yml/badge.svg?branch=main)
![OLP wire v0.1](https://img.shields.io/badge/OLP%20wire-v0.1-1f6feb?style=flat-square)
[![Docs](https://img.shields.io/website?url=https%3A%2F%2Fterryncew.github.io%2Fopenline-core%2F&label=Docs%20(Pages))](https://terryncew.github.io/openline-core/)
![License: MIT](https://img.shields.io/badge/License-MIT-22c55e.svg?style=flat-square)

**Status: Experimental protocol for multi-agent coordination**

OLP is a structured wire format for AI agents to exchange reasoning graphs instead of unstructured text. The goal: make agent plans auditable, merges conflict-aware, and changes explicit.

## What Problem Does This Solve?

When multiple AI agents collaborate (or when one agent reasons over time), they typically exchange raw text. This makes it hard to:
- **Audit reasoning**: Which claims depend on which evidence?
- **Detect contradictions**: Are we asserting X and ¬X simultaneously?
- **Track changes**: What actually changed between reasoning steps?
- **Prevent loops**: Are we using our conclusion to prove our premise?

OLP addresses this by having agents send **graphs** (nodes = claims/evidence/counters, edges = supports/contradicts/depends) with **structural fingerprints** that make these problems detectable.

## Core Idea

Instead of:
```

“I think X because Y, but Z is a concern, so we should do W”

```
Agents send:
```json
{
  "nodes": [
    {"id":"C1", "type":"Claim", "label":"X"},
    {"id":"E1", "type":"Evidence", "label":"Y"},
    {"id":"Ct1", "type":"Counter", "label":"Z"},
    {"id":"P1", "type":"PlanStep", "label":"W"}
  ],
  "edges": [
    {"src":"E1", "dst":"C1", "rel":"supports"},
    {"src":"Ct1", "dst":"C1", "rel":"contradicts"},
    {"src":"C1", "dst":"P1", "rel":"derives"}
  ],
  "digest": {"b0":1, "cycle_plus":0, "x_frontier":1, ...}
}
```

## What’s Actually Measured

The **5-number digest** tracks graph topology:

- **b₀**: Connected components (1 = unified reasoning, >1 = disconnected arguments)
- **cycle_plus**: Support cycles (do we use claim A to prove claim A?)
- **x_frontier**: Unresolved contradictions (claims with active Counter nodes)
- **s_over_c**: Support-to-contradiction ratio
- **depth**: Longest dependency chain (deep chains are fragile)

The **holonomy gap (Δ_hol)** measures how much the digest changed after an operation. Large spikes suggest “smoothing over” structural problems.

## Guards (What Gets Rejected)

The server enforces three rules:

1. **cycle_plus ≤ 4**: Prevents circular reasoning
1. **x_frontier can only decrease via resolution**: You can’t just delete contradictions; you must address them with Assumption or Counter nodes
1. **Δ_hol spikes require explanation**: Large structural changes need new nodes justifying them

These are **heuristics**, not proofs of correctness. They catch common failure modes.

## Design Metaphors vs. Actual Implementation

OpenLine borrows terminology from differential geometry and topology:

- **“Holonomy gap”**: Borrowed from parallel transport in curved spaces. Here it’s just `||digest_after - digest_before||₁` (L1 norm of digest changes). Useful as a delta metric, not a literal geometric measurement.
- **“Curvature” (kappa_eff)**: Heuristic for reasoning stress, not Ricci curvature.
- **“Coherence” (phi_sem, phi_topo)**: Computed from node weights and edge patterns, not information-theoretic mutual information.

The metaphors guide design decisions about what to measure. The actual measurements are graph statistics.

## Quick Start

```bash
# Install dependencies
uv sync

# Run demo server
uv run examples/quickstart.py
```

Server runs at `http://127.0.0.1:8088/frame`

Send a frame:

```bash
curl -X POST http://127.0.0.1:8088/frame \
  -H 'Content-Type: application/json' \
  -d @examples/sample_frame.json
```

## Wire Format (v0.1)

**Nodes**: `Claim | Evidence | Counter | Assumption | Constraint | PlanStep | Outcome | Principle | Motif`

**Edges**: `supports | contradicts | depends_on | derives | updates | instantiates | illustrates`

**Operations**: `add_node | del_node | add_edge | del_edge | retype | reweight | merge | split | homotopy`

Full schema: [`openline/schema.py`](openline/schema.py)

## Architecture

```
openline/
├── schema.py         # Pydantic models (frozen v0.1 wire)
├── digest.py         # 5-number fingerprint computation
├── guards.py         # Cycle/contradiction/delta checks
├── telem.py          # Coherence/curvature heuristics
├── crypto.py         # Witness marks (Merkle, signatures)
└── adapters/
    ├── fastapi_app.py    # HTTP server
    └── stitch_bridge.py  # Integration with Stitch scheduler
```

## What This Doesn’t Do

- **Prove logical validity**: Guards catch structural problems, not semantic errors
- **Guarantee agent reliability**: This is infrastructure for auditing, not a correctness proof
- **Replace prompting**: Agents still need good prompts to generate coherent frames
- **Work automatically**: You need to build agent logic that produces OLP frames

## Validation Status

**Tested**: Schema validation, digest computation, guard logic  
**Untested**: Whether this actually improves multi-agent coordination in practice

This is research infrastructure. It’s working code, but the hypothesis (structured graphs improve agent reliability) needs empirical demonstration.

## Use Cases (Hypothetical)

- **Multi-agent debate**: Agents exchange claim/counter graphs
- **RAG planning**: Break retrieval+reasoning into auditable steps
- **Tool orchestration**: Track which tool calls depend on which results
- **Version control for reasoning**: Diff frames to see what changed

## Contributing

Small, focused PRs welcome:

- If you touch `openline/schema.py`, include migration note + tests
- Maintain ≥90% test coverage (`pytest --cov`)
- Run `ruff` and `mypy` before pushing
- Update examples if behavior changes

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for details.

## Roadmap

- [ ] WebSocket broadcast for multi-agent rooms
- [ ] Persistence adapters (Postgres, S3)
- [ ] Determinism probes (verify digest recomputation is stable)
- [ ] Multi-frame Stitch examples
- [ ] Witness marks (Merkle proofs + Ed25519 signatures)

## License

MIT. Do what you want, credit the project, no warranties.

## Citation

If you use OLP in research:

```bibtex
@software{openline_protocol,
  author = {White, Terrynce},
  title = {Open Line Protocol (OLP)},
  version = {0.1.0},
  url = {https://github.com/terryncew/openline-core},
  year = {2025}
}
```

-----

## FAQ

**Q: Is this proven to improve agent reliability?**  
A: No. It’s testable infrastructure for structured agent communication. Validation needs empirical work.

**Q: What’s with the geometry terminology?**  
A: Design metaphors. “Holonomy gap” is really just a digest diff, “curvature” is a heuristic stress metric. The terms guide what to measure, not literal mathematical claims.

**Q: Should I use this in production?**  
A: Only if you’re willing to debug it. This is v0.1 experimental infrastructure.

**Q: How does this relate to COLE?**  
A: COLE monitors single-agent behavior over time. OLP is for multi-agent coordination. They’re complementary layers.

-----

**OpenLine makes agent reasoning auditable.**  
The protocol is simple. The hard part is getting agents to use it well.
