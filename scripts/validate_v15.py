#!/usr/bin/env python3
import json, sys, pathlib, hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "receipt.v1.5.schema.json"  # informational only
RECEIPT = ROOT / "docs" / "receipt.latest.json"
POLICY  = ROOT / "policies" / "policy.v1.yaml"

def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def must(cond, msg):
    if not cond:
        print(f"[x] {msg}", file=sys.stderr); sys.exit(2)

def main():
    data = json.loads(RECEIPT.read_text())

    # version
    must(data.get("receipt_version") == "olr/1.5", "receipt_version must be 'olr/1.5'")

    # minimal shape
    attrs = data.get("attrs") or {}
    must(attrs.get("status") in ("green","amber","red"), "attrs.status must be green|amber|red")
    policy = data.get("policy") or {}
    must(isinstance(policy.get("policy_id",""), str) and policy["policy_id"], "policy.policy_id required")

    # size guard
    raw = json.dumps(data, separators=(",",":")).encode("utf-8")
    is_amber_or_red = attrs["status"] in ("amber","red")
    cap = 800 if is_amber_or_red else 640
    must(len(raw) <= cap, f"size_guard exceeded: {len(raw)} bytes > {cap}")

    # policy hash check (if present and file exists)
    want = policy.get("policy_hash")
    if POLICY.exists():
        have = sha256_file(POLICY)
        if want:
            must(want == have, f"policy_hash mismatch: receipt={want} repo={have}")
        else:
            print(f"[!] receipt missing policy_hash; repo hash is {have}", file=sys.stderr)

    # dials presence rule
    dials = ((data.get("telem") or {}).get("dials") or None)
    if attrs["status"] == "green":
        must(dials is None, "GREEN receipts must not include telem.dials")
    else:
        if dials:
            for k in ("dphi_dk_q8","d2phi_dt2_q8","fresh_ratio_q8"):
                must(k in dials, f"telem.dials.{k} missing on AMBER/RED")
                v = dials[k]; must(isinstance(v,int) and 0<=v<=255, f"{k} must be 0..255")
            must(dials.get("scale") == "q8_signed", "telem.dials.scale must be 'q8_signed'")

    print("[ok] receipt v1.5 valid, size within guard, policy OK.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
