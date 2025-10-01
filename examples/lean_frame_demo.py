# examples/lean_frame_demo.py
from adapters.lean_frame_builder import build_frame
from pprint import pprint

text = ("Claim: This adapter emits a small reasoning graph. "
        "Because we use simple evidence markers, structure is measurable. "
        "Therefore, κ can reflect density vs. structure without chain-of-thought.")
frame = build_frame(text)
pprint({"digest": frame["digest"], "telem": frame["telem"]})
