#!/usr/bin/env python3
import json, sys
from jsonschema import Draft202012Validator

if len(sys.argv) != 2:
    print("Usage: python recipes/validate.py <frame.json>")
    sys.exit(2)

schema = json.load(open('recipes/schemas/olp-frame.schema.json'))
data = json.load(open(sys.argv[1]))
v = Draft202012Validator(schema)
errs = list(v.iter_errors(data))
if errs:
    for e in errs:
        print(f"- {e.message}")
    sys.exit(1)
print("OK")
