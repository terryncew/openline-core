# examples/build_frame_from_text.py
from adapters.frames.frame_builder import build_frame_from_text
import sys, json, pathlib

text = " ".join(sys.argv[1:]) or """The treatment reduces mortality. Because two RCTs report hazard ratios below 0.8, confidence is moderate. However, a re-analysis suggests measurement bias. According to https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12345, results replicate."""
frame = build_frame_from_text(text, stream_id="example", t_logical=1)
print(json.dumps(frame["telem"], indent=2))
out = pathlib.Path("artifacts"); out.mkdir(parents=True, exist_ok=True)
(out/"frame.json").write_text(json.dumps(frame, indent=2), encoding="utf-8")
print("[ok] wrote artifacts/frame.json")
