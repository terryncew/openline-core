#!/usr/bin/env python3
from hashlib import sha256
import re, pathlib

p = pathlib.Path("policies/policy.v1.yaml")
b = p.read_bytes()
# CI-style canonicalization: drop policy_hash line and normalize newlines to LF
txt = re.sub(rb'^\s*policy_hash:.*\n', b'', b, flags=re.MULTILINE).replace(b"\r\n", b"\n")
print("sha256:" + sha256(txt).hexdigest())
