# Structured Outputs → OpenLine Frame (OLP)

Paste this prompt into your system/instructions to force a valid OLP frame:

Return ONLY a JSON object matching this contract (no prose):
- id: string
- ts: ISO 8601 timestamp (UTC)
- agent: string
- nodes: array of { id: string, type: one of [Claim,Evidence,Question,Action,Observation], text: string }
- edges: array of { from: string, to: string, type: one of [supports,contradicts,elaborates,causes,refutes] }
- telemetry: { shape: [n_nodes, n_edges, density, cycles, contradictions], holonomy: number }

Rules:
1) No extra keys.
2) Every edge.from/to must reference an existing node id.
3) Set telemetry.shape as:
   - shape[0] = number of unique nodes,
   - shape[1] = number of edges,
   - shape[2] = n_edges / max(1, n_nodes*(n_nodes-1)/2),
   - shape[3] = cycles>=0,
   - shape[4] = contradictions>=0.

Example node intent:
- Claim: testable statement
- Evidence: data/citation
- Question: targeted uncertainty
- Action: next step
- Observation: measurement/outcome

Return the JSON now.
