#!/usr/bin/env python3
"""Fix starved_thermal pads by switching them to full zone connection.

Usage (KiCad 9 container): fix_starved_pads.py <board.kicad_pcb> <drc.json> [--dry]
Reads starved_thermal findings from the DRC JSON, maps item descriptions
(`Pad N [/net] of REF`) to pads, sets SetLocalZoneConnection(FULL), saves.
"""
import json
import re
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path, drc_path = sys.argv[1], sys.argv[2]
drc = json.load(open(drc_path))
board = pcbnew.LoadBoard(board_path)

targets = set()
pat = re.compile(r"^(?:SMD |PTH )?[Pp]ad (\S+) \[", re.M)
for v in drc.get("violations", []):
    if v["type"] != "starved_thermal":
        continue
    ref = None
    pad = None
    for it in v["items"]:
        d = it["description"]
        m = pat.match(d)
        if m:
            pad = m.group(1)
        mo = re.search(r"of (\S+)(?: on|$)", d)
        if mo:
            ref = mo.group(1)
    if ref and pad:
        targets.add((ref, pad))
    else:
        print("SKIP", v["items"])

fixed = 0
for fp in board.GetFootprints():
    if fp.GetReference() not in {r for r, _ in targets}:
        continue
    for pad in fp.Pads():
        if (fp.GetReference(), pad.GetPadName()) in targets:
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            fixed += 1
            print("full-connect", fp.GetReference(), pad.GetPadName())

print("fixed", fixed)
if fixed and not DRY:
    zones = list(board.Zones())
    pcbnew.ZONE_FILLER(board).Fill(zones)
    board.Save(board_path)
    print("saved")
