# adapters/frames/frame_builder.py
# v0.2 — bounded-cost text→OLP frame adapter with confidence & multi-signal metrics
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math, json, re
from collections import Counter, defaultdict

# --- lightweight tokenization & cosine ---------------------------------------
_WORD = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?")

def sent_split(text: str) -> List[str]:
    # cheap sentence split: ., !, ? boundaries
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in parts if s.strip()]

def tok(sent: str) -> List[str]:
    return [w.lower() for w in _WORD.findall(sent)]

def vec(sent: str) -> Counter:
    return Counter(tok(sent))

def cos(a: Counter, b: Counter) -> float:
    if not a or not b: return 0.0
    dot = sum(a[k]*b.get(k,0) for k in a)
    na = math.sqrt(sum(v*v for v in a.values())); nb = math.sqrt(sum(v*v for v in b.values()))
    if na == 0 or nb == 0: return 0.0
    return dot/(na*nb)

# --- graph scaffolding --------------------------------------------------------
@dataclass
class Node:
    id: str
    type: str   # "Claim" | "Evidence" | "Assumption" | "Source"
    label: str
    weight: float = 1.0

@dataclass
class Edge:
    src: str
    dst: str
    rel: str    # "supports" | "contradicts" | "depends_on" | "cites"
    weight: float = 1.0

SUPPORT_TOKENS = ("because", "therefore", "so that", "so,", "hence", "thus")
CONTRA_TOKENS  = ("however", "but", "nevertheless", "nonetheless", "although", "yet")
CITE_TOKENS    = ("doi:", "pmid", "pmcid", "according to", "as cited", "see:", "arxiv", "usc", "§", "http://", "https://")

def _authority_score(s: str) -> float:
    s_l = s.lower()
    if "doi:" in s_l or "pmcid" in s_l or "pmid" in s_l: return 1.00
    if re.search(r"https?://.*\.(gov|edu)/", s_l): return 1.00
    if "arxiv" in s_l or "usc" in s_l: return 0.85
    if "wikipedia.org" in s_l: return 0.70
    if "http://" in s_l or "https://" in s_l: return 0.30
    return 0.00

def _extract_nodes_edges(text: str) -> Tuple[List[Node], List[Edge], float]:
    """
    Heuristic extraction with strict caps (bounded-cost).
    - First sentence -> Claim.
    - Sentences with SUPPORT_TOKENS -> Evidence supports last Claim.
    - Sentences with CONTRA_TOKENS  -> Evidence contradicts last Claim.
    - Sentences with CITE_TOKENS    -> Source node cited by last Evidence/Claim.
    """
    sents = sent_split(text)
    nodes: List[Node] = []
    edges: List[Edge] = []
    if not sents:
        return nodes, edges, 0.0

    # caps for bounded work
    max_sents = min(len(sents), 8)                # ≤8 sentences
    max_supports, max_contras = 4, 2

    # seed first claim
    nid_counter = 1
    claim_id = f"C{nid_counter}"; nid_counter += 1
    nodes.append(Node(claim_id, "Claim", sents[0], 1.0))
    last_claim = claim_id
    supports_used, contras_used = 0, 0

    for s in sents[1:max_sents]:
        s_l = s.lower()
        # classify
        is_contra  = any(t in s_l for t in CONTRA_TOKENS)
        is_support = any(t in s_l for t in SUPPORT_TOKENS)
        has_cite   = any(t in s_l for t in CITE_TOKENS)

        if is_contra and contras_used < max_contras:
            eid = f"E{nid_counter}"; nid_counter += 1
            nodes.append(Node(eid, "Evidence", s, 1.0))
            edges.append(Edge(eid, last_claim, "contradicts", 1.0))
            contras_used += 1
        elif (is_support or not is_contra) and supports_used < max_supports:
            eid = f"E{nid_counter}"; nid_counter += 1
            nodes.append(Node(eid, "Evidence", s, 1.0))
            edges.append(Edge(eid, last_claim, "supports", 1.0))
            supports_used += 1

        if has_cite:
            sid = f"S{nid_counter}"; nid_counter += 1
            nodes.append(Node(sid, "Source", s, 1.0))
            # cite last content node (prefer latest Evidence)
            target = nodes[-2].id if len(nodes) >= 2 else last_claim
            edges.append(Edge(target, sid, "cites", 1.0))

    # confidence: coverage × link_syntax
    coverage = min(1.0, (len(nodes)+len(edges))/max(1.0, 1+len(sents)))
    link_syntax = 1.0 if any(any(t in n.label.lower() for t in CITE_TOKENS) for n in nodes) else 0.5
    conf = min(1.0, coverage * link_syntax)
    return nodes, edges, conf

# --- digest & topo helpers ----------------------------------------------------
def _components(nodes: List[Node], edges: List[Edge]) -> int:
    # undirected components
    nbr = defaultdict(set)
    for e in edges:
        nbr[e.src].add(e.dst); nbr[e.dst].add(e.src)
    seen=set(); comps=0
    for n in nodes:
        if n.id in seen: continue
        comps+=1
        stack=[n.id]
        while stack:
            u=stack.pop()
            if u in seen: continue
            seen.add(u)
            stack.extend(v for v in nbr[u] if v not in seen)
    return comps

def _cycle_plus(nodes: List[Node], edges: List[Edge]) -> int:
    # count simple directed support cycles (tiny graphs)
    out=0
    sup = defaultdict(list)
    for e in edges:
        if e.rel=="supports":
            sup[e.src].append(e.dst)
    ids = [n.id for n in nodes]
    for a in ids:
        # small triangles a->b->c->a
        for b in sup.get(a, []):
            for c in sup.get(b, []):
                if a in sup.get(c, []):
                    out += 1
    return out

def _longest_path(nodes: List[Node], edges: List[Edge]) -> int:
    # DAG-ish estimate (ignore 'cites'); break on repeats
    nxt = defaultdict(list)
    for e in edges:
        if e.rel in ("supports","contradicts","depends_on"):
            nxt[e.src].append(e.dst)
    best=0
    def dfs(u, seen):
        nonlocal best
        if u in seen: return
        seen.add(u)
        best = max(best, len(seen)-1)
        for v in nxt.get(u, []):
            dfs(v, set(seen))
    for n in nodes:
        dfs(n.id, set())
    return best

def _counts(edges: List[Edge]) -> Tuple[int,int,int]:
    S = sum(1 for e in edges if e.rel=="supports")
    K = sum(1 for e in edges if e.rel=="contradicts")
    C = _cycle_plus([], [e for e in edges if e.rel=="supports"])
    return S, K, C

# --- metrics (phi_topo, phi_sem, kappa, drift) --------------------------------
def phi_topo(nodes: List[Node], edges: List[Edge]) -> float:
    N, E = len(nodes), len(edges)
    S, K, C = _counts(edges)
    D = _longest_path(nodes, edges) / 6.0  # normalize ~[0,1] (cap at path=6)
    x_frontier = K  # unresolved contradictions proxy
    lin = (
        0.40*math.log(1.0 + E/(N+1.0)) +
        0.20*D -
        0.35*C -
        0.25*x_frontier +
        0.30*(S/(K+1.0))
    )
    return 1.0/(1.0+math.exp(-lin))

def _avg_support_cos(nodes: List[Node], edges: List[Edge]) -> float:
    text = {n.id:n.label for n in nodes}
    pairs=[]
    for e in edges:
        if e.rel=="supports" and e.src in text and e.dst in text:
            pairs.append(cos(vec(text[e.src]), vec(text[e.dst])))
    if not pairs: return 0.0
    return sum(pairs)/len(pairs)

def sdi(text: str) -> float:
    sents = sent_split(text)
    if len(sents)<2: return 0.0
    sims=[]
    for a,b in zip(sents[:-1], sents[1:]):
        sims.append(cos(vec(a), vec(b)))
    return max(0.0, min(1.0, 1.0 - (sum(sims)/len(sims) if sims else 0.0)))

def phi_sem(nodes: List[Node], edges: List[Edge], raw_text: str) -> float:
    return max(0.0, min(1.0, 0.6*_avg_support_cos(nodes, edges) + 0.4*sdi(raw_text)))

def _entropy(tokens: List[str]) -> float:
    if not tokens: return 0.0
    c=Counter(tokens); total=sum(c.values())
    probs=[v/total for v in c.values()]
    H=-sum(p*math.log(p+1e-12) for p in probs)
    # normalize by log |V| (≤1)
    return H/(math.log(len(c)+1e-12)+1e-12)

def _length_z(tokens: List[str], mu: float=250.0, sigma: float=100.0) -> float:
    return (len(tokens)-mu)/max(1.0, sigma)

def kappa_eff(nodes: List[Node], edges: List[Edge], raw_text: str) -> Tuple[float, float, float, float]:
    # compute κ_base, and components: rho, S*, cite_score
    tokens = tok(raw_text)
    zL = _length_z(tokens)
    Hs = _entropy(tokens)         # normalized 0..~1.0
    r  = min(1.0, len(sent_split(raw_text))/10.0)  # proxy "rate"
    rho = 0.45*zL + 0.35*Hs + 0.20*r
    phiT = phi_topo(nodes, edges)
    phiS = phi_sem(nodes, edges, raw_text)
    S_star = 0.45*phiT + 0.45*phiS + 0.10*(1.0/(1.0 + _counts(edges)[2] + _counts(edges)[1]))
    lin = 1.4 * (rho / (S_star + 1e-6))
    kappa_base = 1.0/(1.0+math.exp(-lin))
    # citation relief (multiplicative): use node labels to estimate authority
    auth = max((_authority_score(n.label) for n in nodes), default=0.0)
    cite_score = auth  # no NLI here; keep simple
    kappa = kappa_base * (1.0 - 0.30 * cite_score)
    return max(0.0,min(1.0,kappa)), rho, S_star, cite_score

def holonomy_delta(prev_digest: Dict, cur_digest: Dict) -> float:
    keys = ("b0","cycle_plus","x_frontier","s_over_c","depth")
    return sum(abs(float(cur_digest.get(k,0.0)) - float(prev_digest.get(k,0.0))) for k in keys)

# --- public API ---------------------------------------------------------------
def build_frame_from_text(text: str, stream_id: str="olp-stream", t_logical: int=1, prev_digest: Dict|None=None) -> Dict:
    nodes, edges, conf = _extract_nodes_edges(text)
    N, E = len(nodes), len(edges)
    S, K, C = _counts(edges)
    depth = _longest_path(nodes, edges)
    b0 = _components(nodes, edges)
    s_over_c = (S / (K if K>0 else 1.0))
    x_frontier = K  # proxy unresolved contradictions

    # telemetry
    phiT = phi_topo(nodes, edges)
    phiS = phi_sem(nodes, edges, text)
    kappa, rho, S_star, cite_score = kappa_eff(nodes, edges, text)
    digest = {"b0": b0, "cycle_plus": C, "x_frontier": x_frontier, "s_over_c": s_over_c, "depth": depth}
    delta_hol = holonomy_delta(prev_digest or {}, digest)

    frame = {
        "stream_id": stream_id,
        "t_logical": t_logical,
        "gauge": "sym",
        "units": "confidence:0..1,cost:tokens",
        "nodes": [n.__dict__ for n in nodes],
        "edges": [e.__dict__ for e in edges],
        "digest": digest,
        "morphs": [],
        "telem": {
            "phi_sem": round(phiS,4),
            "phi_topo": round(phiT,4),
            "delta_hol": round(delta_hol,4),
            "kappa_eff": round(kappa,4),
            "rho": round(rho,4),
            "S_star": round(S_star,4),
            "cite_score": round(cite_score,4),
            "conf": round(conf,3),
            "cost_tokens": len(tok(text)),
        }
    }
    return frame

if __name__=="__main__":
    import sys, pathlib
    txt = " ".join(sys.argv[1:]) or "Because randomized trials show effect sizes, the claim holds. However, a contrary cohort study suggests bias. According to doi:10.xxxx, the effect persists."
    f = build_frame_from_text(txt, "demo", 1)
    out = pathlib.Path("artifacts"); out.mkdir(parents=True, exist_ok=True)
    (out/"frame.json").write_text(json.dumps(f, indent=2), encoding="utf-8")
    print(json.dumps({"kappa":f["telem"]["kappa_eff"], "Δhol":f["telem"]["delta_hol"], "C":f["digest"]["cycle_plus"], "X":f["digest"]["x_frontier"], "conf":f["telem"]["conf"]}, indent=2))
