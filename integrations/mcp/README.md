# OpenLine ↔ MCP (Minimal Adapter)

This folder gives you:
- `mcp-tool.json` — a simple tool manifest describing an `openline.stitch` tool.
- `server_stub.py` — a tiny JSON-RPC stdin/stdout server that handles `openline.stitch`.
- `client_example.py` — sends a JSON-RPC request with an OLP frame to the server.

No external deps. Run locally:

```bash
# Terminal 1
python integrations/mcp/server_stub.py

# Terminal 2
python integrations/mcp/client_example.py
