# metrics/kappa.py
from __future__ import annotations
import math, re
from collections import Counter

TOK = re.compile(r"[A-Za-z0-9_'-]+")
SUPPORT = re.compile(r"(^|\s)(therefore|thus|hence|because)\b|^\s*so\b", re.I)
ATTACK  = re.compile(r"\b(however|but|although|nevertheless|nonetheless|on the other hand|contradict|refute)\b", re.I)

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

def rhetorical_rate(text: str) -> float:
    sents = re.split(r"(?<=[.!?])\s+|•\s+", (text or "").strip())
    if not sents: return 0.0
    hits = sum(1 for s in sents if (SUPPORT.search(s) or ATTACK.search(s)))
    return hits/len(sents)

def compute_kappa(length_tokens: int, mu_len: float, std_len: float,
                  Hs: float, rate: float, phi_topo: float, phi_sem_proxy: float) -> float:
    zL = 0.0 if std_len < 1e-6 else max(-3.0, min(3.0, (length_tokens - mu_len)/std_len))
    rho = 0.45*abs(zL) + 0.35*Hs + 0.20*rate
    Sstar = max(1e-3, 0.45*phi_topo + 0.45*phi_sem_proxy + 0.10)
    return sigma(1.4 * rho / Sstar)
