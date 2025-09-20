# LangGraph Node: OpenLine Guard

A minimal node that:
1) Validates an OLP frame (node/edge refs, cycle count, contradiction count).
2) Emits a `receipt` dict you can log/trace.
3) Returns the (possibly annotated) `frame`.

Usage (pseudo):

```python
from integrations.langgraph.openline_node import olp_guard_node
from langgraph.graph import StateGraph

graph = StateGraph(dict)
graph.add_node("olp_guard", olp_guard_node)
graph.set_entry_point("olp_guard")
app = graph.compile()

out = app.invoke({"frame": YOUR_FRAME})
print(out["receipt"])
