# Biosecurity Screening Receipts (v0.1)

**Purpose**  
A safe, portable audit artifact for DNA/RNA order screening. No sequences. No fragments. Just signed metadata that explains *what screened what, with which rules, and why the decision was made*.

**Why this helps**
- **Upgrades you can verify:** compare decisions before/after a ruleset or model change.
- **Interoperability:** vendor-neutral JSON; travels with purchase orders, incidents, or regulator requests.
- **Drift visibility:** `delta_hol` flags silent shifts in decisions for similar orders.

## What a receipt contains
- `request`: timestamp, order ID, org (optional).
- `provenance`: engine name/version, ruleset hash, model name/version, model weights hash, policy/prompt hash.
- `signals` (metadata only):
  - `tox_sim`: coarse bucket to restricted families.
  - `frag_hits`: k-mer hit count + coverage fraction.
  - `novelty_index`: low/medium/high.
  - `heuristics`: booleans (e.g., `codon_shuffle_suspect`).
  - `delta_hol`: drift vs. recent decisions on *similar* orders (non-reversible similarity bucket).
- `decision`: `ALLOW`/`HOLD`/`BLOCK` and the guards that fired.
- Optional `human_eval`: 60-second verdict + note.
- `policy`: sharing scope and retention.
- `signatures`: ed25519 over the whole JSON.

## Privacy & safety posture
- **Never** include raw sequences or fragments.
- Hash all sensitive files (`ruleset_hash`, `weights_hash`, `prompt_policy_hash`) with `sha256:`.
- Use **non-reversible similarity buckets** for `delta_hol` (e.g., salted LSH sketch → bucket ID). Do not persist sketches that allow reconstruction.

## Minimal integration (outline)
1. Emit a JSON conforming to `bio.screening.v0.1.schema.json` at decision time.
2. Compute `delta_hol` as the JSD (0–1) between a fixed-length feature vector for this order and the EWMA of prior vectors **within the same similarity bucket**. Features may include:
   - normalized `frag_hits.hits`, `frag_hits.covered_pct`
   - ordinal `novelty_index` (0/0.5/1)
   - boolean heuristics (0/1)
   - encoded `tox_sim` bucket (0–1)
3. Sign the receipt (ed25519). Store internally; share per `policy.share`.
4. Keep a tiny **conformance set** of synthetic “should-flag” and “should-pass” metadata cases; test each release.

## Do / Don’t
- **Do** minimize metadata and keep `pii=false`.
- **Do** publish monthly aggregates (counts by verdict; drift trend), not content.
- **Don’t** expose rules or exact thresholds publicly; only their hashes.
- **Don’t** publish any sequence-derived material beyond coarse buckets.

## Example
See `docs/examples/bio.receipt.example.json`.
