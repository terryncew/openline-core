OpenLine Protocol (OLP)
AI agents speaking geometry, not paragraphs.
OLP is a minimal, machine-readable protocol for representing an agent's reasoning as a graph. This makes agent plans auditable, conflict-aware, and observable at runtime.
Quickstart (60 seconds)
1. Prerequisite: Install uv
pip install uv

2. Clone and Run the Server
git clone https://github.com/terryncew/openline-core.git
cd openline-core

# Install dependencies and start the server
uv sync --extra server
uv run olp-server --port 8088

3. Send a Frame (in a second terminal)
# In the same directory (openline-core)
uv run examples/quickstart.py

Expected output: You'll see a JSON response confirming the frame was received and processed.
{"ok": true, "digest": {"b0": 1, ...}, "telem": {"kappa_eff": 0.3, ...}}
What You Get
 * Frozen Wire Schema (v0.1) — A typed, dependable Pydantic schema for agent reasoning.
 * Runtime Guards — Built-in checks to prevent common failure modes like self-reinforcing loops, silent evidence deletion, and unexplainable state jumps.
 * 5-Number Digest — A compact "fingerprint" of the reasoning graph's shape and health.
 * Built-in Telemetry — Coherence (κ), drift (Δ), and other metrics to auto-throttle agents.
The Frame Schema
An OLP Frame is a small graph with typed nodes and edges.
Node Types
Claim | Evidence | Counter | Assumption | PlanStep | Outcome | Principle
Edge Types
supports | contradicts | depends_on | derives | updates | instantiates
The Digest (5-Number Fingerprint)
 * b₀ (components) — Is this one connected argument, or many disconnected islands?
 * cycle_plus (support cycles) — Is the agent "proving itself with itself"?
 * x_frontier (live contradictions) — How many active contradictions need resolution?
 * s_over_c (support ratio) — Is evidence and support outpacing contradiction?
 * depth (dependency chain) — How deep is the longest reasoning chain? (Risk of fragility).
Holonomy Gap (Δ_hol)
Δ_hol = ||digest_post − digest_pre||₁ — Measures "order-debt" or drift across an operation. A large gap means the state changed in a significant, potentially incoherent way.
Guards: What They Prevent
The server automatically runs these checks on every submitted frame:
 * Self-Reinforcing Myths: Fails if cycle_plus exceeds a cap (e.g., > 4).
 * Silent Objection Erasure: Fails if x_frontier drops by deleting a counter-claim instead of resolving it.
 * "Too-Clean" Rewrites: Fails if Δ_hol spikes without an explanatory node justifying the large change.
The Coordination Pattern
OLP enables robust, multi-agent collaboration without a central coordinator:
SYNC (fetch prior state) → MEASURE (locally compute proposed changes) → STITCH (commit valid changes back).
This conflict-aware pattern allows different models to work on the same problem while maintaining shared invariants.
Run Tests & Checks
uv run ruff check .
uv run mypy openline
uv run pytest -q --cov=openline

Troubleshooting
 * uv: command not found → Run pip install uv.
 * Port 8088 already in use → Start the server on a different port: uv run olp-server --port 8090 and update your client.
 * Import errors: Make sure you've run uv sync --extra server in the project root to install all dependencies.
Cite This Work
If you use OpenLine in research, policy, or production systems, please cite:
BibTeX
@software{white_openline_cole_2025,
  author  = {Terrynce White},
  title   = {OpenLine Protocol and COLE: Auditable Receipts for AI Runs},
  year    = {2025},
  url     = {https://github.com/terryncew/openline-core},
  note    = {Receipt-per-run with κ (stress) and Δ_{hol} (path drift)}
}

APA
White, T. (2025). OpenLine Protocol and COLE: Auditable receipts for AI runs (κ, Δhol). GitHub. https://github.com/terryncew/openline-core
