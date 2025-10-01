# adapters/frame_builder.py
from __future__ import annotations
import math, re, zlib
from collections import Counter, defaultdict

TOK = re.compile(r"[A-Za-z0-9_'-]+")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|•\s+")
SUPPORT = re.compile(r"(^|\s)(therefore|thus|hence|because)\b|^\s*so\b", re.I)
ATTACK  = re.compile(r"\b(however|but|although|nevertheless|nonetheless|on the other hand|contradict|refute)\b", re.I)
ASSUME  = re.compile(r"\b(assume|suppose|hypothesize|let us suppose|let's assume)\b", re.I)

def sentences(text: str): 
    t = (text or "").strip()
    return [s.strip() for s in re.split(SENT_SPLIT, t) if s.strip()]

def bow(s: str) -> Counter: 
    return Counter(w.lower() for w in TOK.findall(s or ""))

def cosine(a: Counter, b: Counter) -> float:
    if not a or not b: return 0.0
    ks = set(a) | set(b)
    num = sum(a[k]*b[k] for k in ks)
    den = (sum(v*v for v in a.values())**0.5) * (sum(v*v for v in b.values())**0.5)
    return (num/den) if den else 0.0

def compress_ratio(text: str) -> float:
    raw = (text or "").encode("utf-8")
    if not raw: return 1.0
    return len(zlib.compress(raw, 6))/max(1, len(raw))

def sigma(x: float) -> float:
    if x >= 0: 
        z = math.exp(-x); return 1/(1+z)
    z = math.exp(x); return z/(1+z)

def structural_entropy(text: str) -> float:
    toks = [w.lower() for w in TOK.findall(text or "")]
    if not toks: return 0.0
    total = len(toks); freq = Counter(toks)
    H = -sum((c/total)*math.log(max(1e-12, c/total)) for c in freq.values())
    Hmax = math.log(len(freq)) if freq else 1.0
    return H/max(1e-12, Hmax)

def sdi(text: str) -> float:
    sents = sentences(text)
    if len(sents) < 2: return 0.0
    bows = [bow(s) for s in sents]
    sims = [cosine(bows[i-1], bows[i]) for i in range(1, len(bows))]
    return max(0.0, min(1.0, 1.0 - (sum(sims)/len(sims))))

def classify_sentence(s: str) -> str:
    if ASSUME.search(s): return "Assumption"
    if SUPPORT.search(s): return "Evidence"
    return "Claim"

def count_cycles(nodes, edges) -> int:
    g = defaultdict(list)
    for e in edges: g[e["src"]].append(e["dst"])
    color = {}; cycles = 0
    def dfs(u):
        nonlocal cycles
        color[u] = 1
        for v in g[u]:
            if color.get(v,0)==0: dfs(v)
            elif color.get(v)==1: cycles += 1
        color[u] = 2
    for n in nodes:
        if color.get(n["id"],0)==0: dfs(n["id"])
    return cycles

def max_depth(nodes, edges) -> int:
    g = defaultdict(list); indeg = Counter()
    for e in edges: g[e["src"]].append(e["dst"]); indeg[e["dst"]] += 1
    roots = [n["id"] for n in nodes if indeg[n["id"]]==0] or ([nodes[0]["id"]] if nodes else [])
    best = 0
    def dfs(u, d):
        nonlocal best
        best = max(best, d)
        for v in g[u]: dfs(v, d+1)
    for r in roots: dfs(r, 1)
    return best

def compute_phi_topo(N,E,D,C,X,S):
    a1,a2,a3,a4,a5 = 0.40,0.20,0.35,0.25,0.30
    raw = a1*math.log(1.0 + E/(N+1.0)) + a2*D - a3*C - a4*X + a5*(S/(X+1.0))
    return sigma(raw)

def compute_phi_sem_proxy(text: str) -> float:
    SDI = sdi(text)                 # 0..1, higher = more progression
    CR  = compress_ratio(text)      # lower = less redundancy
    return max(0.0, min(1.0, 0.6*SDI + 0.4*max(0.0, 1.0-CR)))

def build_frame(text: str, prev_digest: dict|None) -> dict:
    sents = sentences(text)
    nodes, edges = [], []
    for i, s in enumerate(sents):
        ntype = classify_sentence(s)
        nid = f"{ntype[0]}{i+1}"
        nodes.append({"id": nid, "type": ntype, "label": s, "weight": 1.0})
        if i == 0: 
            continue
        sid = nodes[i-1]["id"]; tid = nodes[i]["id"]
        if SUPPORT.search(s):      edges.append({"src": sid, "dst": tid, "rel": "supports", "weight": 1.0})
        elif ATTACK .search(s):    edges.append({"src": tid, "dst": sid, "rel": "contradicts", "weight": 1.0})
        elif ASSUME .search(s):    edges.append({"src": tid, "dst": tid, "rel": "depends_on", "weight": 0.8})
    N,E = len(nodes), len(edges)
    S = sum(1 for e in edges if e["rel"]=="supports")
    X = sum(1 for e in edges if e["rel"]=="contradicts")
    C = count_cycles(nodes, edges)
    D = max_depth(nodes, edges)

    digest = {"b0":1, "cycle_plus":C, "x_frontier":X, "s_over_c": (S/max(1,X)), "depth":D}
    vec = ("b0","cycle_plus","x_frontier","s_over_c","depth")
    if prev_digest:
        p = [prev_digest.get(k,0) for k in vec]
        q = [digest.get(k,0)      for k in vec]
        # plain JSD (same shape as in ingest)
        import math
        def _n(v,eps=1e-9):
            s=sum(v); 
            return [eps]*len(v) if s<=0 else [max(eps,x/s) for x in v]
        P,Q=_n(p),_n(q); M=[(pi+qi)/2 for pi,qi in zip(P,Q)]
        def _kl(u,v): return sum(ui*math.log(ui/vi) for ui,vi in zip(u,v))
        delta_hol = 0.5*_kl(P,M)+0.5*_kl(Q,M)
    else:
        delta_hol = 0.0

    telem = {
        "phi_sem_proxy": compute_phi_sem_proxy(text),
        "phi_topo": compute_phi_topo(N,E,D,C,X,S),
        "delta_hol": delta_hol,
        "kappa_eff": None,
        "cost_tokens": len(TOK.findall(text or "")),
    }
    return {"nodes":nodes,"edges":edges,"digest":digest,"telem":telem,"raw_text":text}
