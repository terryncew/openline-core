# tests/test_guards_v02.py
from adapters.frames.frame_builder import build_frame_from_text

def _pull(frame): 
    d=frame["digest"]; t=frame["telem"]
    return t["kappa_eff"], t["delta_hol"], d["cycle_plus"], d["x_frontier"], t["conf"]

def test_dense_good():
    txt="The result is consistent. Because RCTs show effect, we proceed. According to doi:10.1000/xyz, findings replicate. Therefore, policy holds."
    f = build_frame_from_text(txt, "t", 1, prev_digest={"b0":1,"cycle_plus":0,"x_frontier":0,"s_over_c":1.0,"depth":1})
    k, dh, C, X, conf = _pull(f)
    assert conf >= 0.6
    assert dh < 0.5 and X == 0

def test_contradiction_deletion():
    prev={"b0":1,"cycle_plus":0,"x_frontier":3,"s_over_c":0.4,"depth":2}
    txt="The policy is safe. Because prior concerns were resolved, we proceed."
    f = build_frame_from_text(txt, "t", 2, prev_digest=prev)
    k, dh, C, X, conf = _pull(f)
    assert dh >= 0.5 or X==0
