#!/usr/bin/env python3
import json, subprocess, sys, os

# Start server as a subprocess for demo; in practice, your MCP host runs the tool.
server = subprocess.Popen(
    [sys.executable, os.path.join("integrations","mcp","server_stub.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
)

frame = {
  "id": "frame-demo-001",
  "ts": "2025-09-20T17:00:00Z",
  "agent": "demo-agent@openline",
  "nodes": [
    {"id":"c1","type":"Claim","text":"Solar + storage lowers peak costs"},
    {"id":"e1","type":"Evidence","text":"CAISO duck curve shows peak spikes"},
    {"id":"q1","type":"Question","text":"What is TOU payback?"}
  ],
  "edges": [
    {"from":"e1","to":"c1","type":"supports"},
    {"from":"q1","to":"c1","type":"elaborates"}
  ]
}

req = {"jsonrpc":"2.0","id":"1","method":"openline.stitch","params":{"frame": frame}}
server.stdin.write(json.dumps(req) + "\n"); server.stdin.flush()
resp = server.stdout.readline().strip()
print("RPC response:\n", resp)
server.terminate()
