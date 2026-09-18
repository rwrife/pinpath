#!/usr/bin/env python3
"""Summarize a KiCad 9 DRC JSON report: unconnected + violation counts by severity/type.

Usage: drc_summary.py <drc.json> [--pairs]
"""
import json
import sys
from collections import Counter

d = json.load(open(sys.argv[1]))
uc = d.get("unconnected_items", [])
vi = d.get("violations", [])
print("unconnected:", len(uc), dict(Counter(i["severity"] for i in uc)))
print("violations:", len(vi), dict(Counter(v["severity"] for v in vi)))
print("types:", dict(Counter(v["type"] for v in vi)))
if "--pairs" in sys.argv:
    for i in uc:
        print(" | ".join(it["description"] for it in i["items"]))
