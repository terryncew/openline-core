# Tester Guide — COLE & OpenLine (Open Alpha)

This guide takes a tester from zero → a signed receipt and a dashboard tile in ~5 minutes.

> **TL;DR**
> - Run the **OpenLine** server (OLP) on port **8088**
> - Send a demo frame
> - Run **COLE** to write `docs/receipt.latest.json`
> - Open the dashboard and sanity‑check **H** and geometry caps

---

## 0) Requirements

- Python **3.11+**
- `pip install uv` (once)
- macOS/Linux/WSL supported; Windows PowerShell works too

---

## 1) Run OpenLine (OLP)

```bash
git clone https://github.com/terryncew/openline-core.git
cd openline-core

# install & run the server
pip install uv
uv sync --extra server
uv run olp-server --port 8088
```

Expected: logs showing the server listening on `http://127.0.0.1:8088`.

**Send a demo frame (new terminal):**
```bash
cd openline-core
uv run examples/quickstart.py
# or: python examples/send_frame.py
```
Expected: JSON reply `{"ok": true, "digest": {...}, "telem": {...}}`.

If port 8088 is busy: start the server with `--port 8090` and re‑run the client.

---

## 2) Score it with COLE

```bash
git clone https://github.com/terryncew/COLE-Coherence-Layer-Engine-.git
cd COLE-Coherence-Layer-Engine-

# install deps
pip install uv && uv sync

# produce a receipt (writes docs/receipt.latest.json)
uv run scripts/ingest_14L.py
```

**Optional: validate / attest / score (if these scripts are present):**
```bash
python scripts/validate_v12.py
python scripts/attest_geometry.py
python scripts/apply_topo_hooks.py
```

**Receipt contents (OLR/1.4L):**
- `openline_frame.digest`: `b0`, `cycle_plus`, `x_frontier`, `s_over_c`, `depth`, `ucr`
- `openline_frame.telem`: `kappa_eff`, `delta_hol`, `evidence_strength`, `phi_topo`, `phi_sem`, `del_suspect`, `cost_tokens`
- top‑level `"status"`: `"green" | "amber" | "red"`

**Caps (fail‑closed):**
- `spectral_max ≤ 2.00`
- `orthogonality_error ≤ 0.08`
- `lipschitz_budget_used ≤ 0.80`

---

## 3) View the dashboard

```bash
# from COLE repo root
python -m http.server -d docs 8000
# then open http://localhost:8000/
```
The top tile shows: worst geometry utilization, loss inflections / policy flips, defect class, and **H**.

---

## 4) Known good / bad receipts

Try the examples if present:
- `docs/examples/receipt-good.json` → within caps, **H** is green‑ish
- `docs/examples/receipt-bad.json` → breach (e.g., `spectral_max`), **QUENCH** event

Use these to sanity‑check rendering and CI steps.

---

## 5) CI snippet (optional)

If running schema checks in GitHub Actions after writing a receipt:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"

- name: Install v1.2 deps
  run: |
    python -m pip install --upgrade pip
    python -m pip install jsonschema

- name: Validate v1.2 schema
  run: python scripts/validate_v12.py

- name: Attest geometry (fail-closed)
  run: python scripts/attest_geometry.py

- name: Apply topology hooks (compute H)
  run: python scripts/apply_topo_hooks.py
```

---

## 6) Troubleshooting

- `uv: command not found` → `pip install uv`
- Client cannot connect → ensure `olp-server` is running on the same port
- No dashboard updates → confirm `docs/receipt.latest.json` exists and refresh the page
- Windows + Python launcher → `py -3.11 -m http.server -d docs 8000`

---

## 7) Scope

- ✅ Observability: topology + geometry caps, one receipt per run (signing optional)
- ✅ Early‑warning: highlights drift/instability and hard defects
- ❌ Truth oracle: does not verify factual correctness; audits structure/behavior

---

## 8) How to cite

**APA**  
White, T. (2025). *OpenLine Protocol and COLE: Auditable receipts for AI runs (κ, Δhol).* GitHub. https://github.com/terryncew/openline-core

**BibTeX**
```bibtex
@software{white_openline_2025,
  author    = {Terrynce White},
  title     = {OpenLine Protocol and COLE: Auditable receipts for AI runs (\kappa, \Delta hol)},
  year      = {2025},
  publisher = {GitHub},
  url       = {https://github.com/terryncew/openline-core},
  note      = {Receipt-per-run with k (stress) and \Delta hol (drift); open source.}
}
```

---

## 9) Version tag

Spec: **olr/1.2** (include this in bug reports).
