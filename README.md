# OpenLine Protocol (OLP)

_AI agents speaking geometry, not paragraphs._

OLP turns model output into a **small graph + digest** and returns a **receipt** you can audit in CI or GitHub Pages.

https://github.com/terryncew/openline-core#quickstart-60-seconds

---

## Quickstart (60 seconds)

**Install uv (once)**
```
pip install uv
```

**Run the server**
```
uv sync --extra server
uv run olp-server --port 8088
```

**Send a demo frame**
```
uv run examples/quickstart.py
# or: python examples/send_frame.py
```

**You should see** a JSON reply like:
```
{"ok": true, "digest": {...}, "telem": {...}}
```

---

## Troubleshooting

- **`uv: command not found` →** `pip install uv`
- **Port in use on 8088 →** `uv run olp-server --port 8090`
- **Client can’t connect →** make sure the server is running on the same port
- **No Pages receipt →** ensure `docs/receipt.latest.json` exists (COLE reads this)

---

## What you get

- **Frame digest (5 numbers):** `b0, cycle_plus, x_frontier, s_over_c, depth`
- **Telemetry:** `phi_topo, phi_sem, delta_hol, kappa_eff, evidence_strength`
- **One JSON artifact per run** that other tools (like **COLE**) can render.

---

## Cite this work

**APA**
> White, T. (2025). *OpenLine Protocol and COLE: Auditable receipts for AI runs (κ, Δhol).* GitHub. https://github.com/terryncew/openline-core

**BibTeX**
```
@software{white_openline_2025,
  author       = {Terrynce White},
  title        = {OpenLine Protocol and COLE: Auditable receipts for AI runs (\kappa, \Delta hol)},
  year         = {2025},
  publisher    = {GitHub},
  url          = {https://github.com/terryncew/openline-core},
  note         = {Receipt-per-run with k (stress) and Δhol (drift); open source.}
}
```
