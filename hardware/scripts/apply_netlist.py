#!/usr/bin/env python3
"""Apply the kicad-cli-exported netlist to the PCB board nets.

Usage: apply_netlist.py <board.kicad_pcb> <netlist.net> <report.json>

The rev-A schematic names its nets with global labels that export as
"/+3V3", "/A:01", ...; DRC schematic-parity therefore expects the board
nets to carry the same leading-slash spelling.  This script renames each
board net to its exported name (by structural membership) and re-verifies
every pad's net against the netlist before saving.
"""
import json
import re
import sys

import pcbnew

board_path, net_path, report_path = sys.argv[1], sys.argv[2], sys.argv[3]
txt = open(net_path).read()

# nets section: (net (code N) (name "X") ... nodes ... )
net_blocks = re.findall(
    r'\(net \(code "\d+"\) \(name "([^"]+)"\).*?(?=\(net \(code|\(nets\)\s*$)',
    txt, re.S)
if not net_blocks:
    raise SystemExit("no nets parsed")

# build ref.pin -> schematic net name
sch_pin = {}
for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)((?:(?!\(net \(code).)*)\)',
                     txt, re.S):
    name, body = m.group(1), m.group(2)
    for nm in re.finditer(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body):
        sch_pin[f"{nm.group(1)}.{nm.group(2)}"] = name
if not sch_pin:
    raise SystemExit("no pad netlist membership parsed")

board = pcbnew.LoadBoard(board_path)

# board-side membership by current net object
from collections import defaultdict
board_membership = defaultdict(list)   # current net name -> [(ref,pad)]
for fp in board.GetFootprints():
    for pad in fp.Pads():
        board_membership[pad.GetNetname()].append(
            (fp.GetReference(), pad.GetPadName()))

# group schematic pins per net name
sch_groups = defaultdict(set)
for key, name in sch_pin.items():
    sch_groups[name].add(key)

renamed = 0
rename_map = {}
for cur_name, members in board_membership.items():
    keys = {f"{r}.{p}" for r, p in members}
    # find the schematic net with identical membership
    match = [n for n, s in sch_groups.items() if s == keys]
    if len(match) == 1:
        want = match[0]
    elif len(match) > 1:
        match.sort(key=lambda n: (n != f"/{cur_name}", n))
        want = match[0]
    else:
        # fall back to name-based guess
        want = f"/{cur_name}" if f"/{cur_name}" in sch_groups else cur_name
    if want != cur_name:
        rename_map[cur_name] = want

applied = []
netnames = board.GetNetsByName()
for cur, want in rename_map.items():
    net = board.FindNet(cur)
    if net is None:
        print(f"WARN net {cur!r} not found for rename")
        continue
    net.SetNetname(want)
    applied.append({"from": cur, "to": want})
    renamed += 1

# verify pad nets
mismatches = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        key = f"{fp.GetReference()}.{pad.GetPadName()}"
        want = sch_pin.get(key)
        if want is None:
            # unnamed/no-net mounting tabs are intentionally absent from the netlist
            if pad.GetNetname() == "":
                continue
            mismatches.append({"pad": key, "issue": "missing from netlist"})
        elif pad.GetNetname() != want:
            mismatches.append({"pad": key, "pcb": pad.GetNetname(), "netlist": want})

print("renamed:", renamed, "pad mismatches:", len(mismatches))
json.dump({"renamed": applied, "mismatches": mismatches},
          open(report_path, "w"), indent=2)
if not mismatches:
    board.Save(board_path)
    print("saved", board_path)
else:
    print("NOT SAVING due to pad mismatches")
    for mm in mismatches[:10]:
        print(" ", mm)
    sys.exit(1)
