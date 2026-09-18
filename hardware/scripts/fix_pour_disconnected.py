#!/usr/bin/env python3
"""Repair DRC pad<->pour unconnected pairs by full-connecting the GND pads.

After a Specctra SES import + refill, tracks carved clearance voids that can
stranding same-net GND pads from the GND pour (DRC unconnected_items entries
citing `Zone 'GND pour ...' [/GND]`). For every such pad, switch the pad to
ZONE_CONNECTION_FULL so it merges with the pour regardless of relief spoke
geometry, refill, and save.

Usage (KiCad 9 container): fix_pour_disconnected.py <board.kicad_pcb> <drc.json> [--dry]
"""
import json
import re
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path, drc_path = sys.argv[1], sys.argv[2]
drc = json.load(open(drc_path))
board = pcbnew.LoadBoard(board_path)

pat = re.compile(r"^(?:SMD |PTH )?[Pp]ad (\S+) \[(.*?)\] of (\S+)")

targets = set()
for u in drc.get("unconnected_items", []):
    descs = [it["description"] for it in u["items"]]
    if all(d.startswith("Zone") for d in descs):
        continue  # pseudo-ratsnest zone-vs-zone artifact
    cites_zone = any(d.startswith("Zone") for d in descs)
    for d in descs:
        m = pat.match(d)
        if m:
            net = m.group(2).lstrip("/")
            # pour-related pair, or a pad<->pad pair that is same-net GND
            if cites_zone or net == "GND":
                targets.add((m.group(3), m.group(1)))

changed = 0
for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        if (ref, pad.GetPadName()) in targets:
            cur = pad.GetLocalZoneConnection()
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            print("full-connect", ref, pad.GetPadName(), "(was", cur, ")")
            changed += 1

print("targets", len(targets), "changed", changed)
if changed and not DRY:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    board.Save(board_path)
    print("saved")
