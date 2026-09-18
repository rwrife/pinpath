#!/usr/bin/env python3
"""Drop dangling tracks (warning-level track_dangling from DRC JSON).

Usage (KiCad 9 container): drop_dangling.py <board.kicad_pcb> <drc.json> [--dry]
Matches each dangling track by net+layer+length from the DRC item description.
"""
import json
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path, drc_path = sys.argv[1], sys.argv[2]
drc = json.load(open(drc_path))
board = pcbnew.LoadBoard(board_path)

netmap = board.GetNetsByName()  # keep the map object alive during iteration
names = {str(name): net.GetNetCode() for name, net in list(netmap.items())}
LayerToId = {
    "F.Cu": pcbnew.F_Cu,
    "B.Cu": pcbnew.B_Cu,
}

removed = 0
for v in drc.get("violations", []):
    if v["type"] != "track_dangling":
        continue
    for it in v["items"]:
        desc = it["description"]
        if "Track [/" not in desc:
            continue
        net = desc.split("[", 1)[1].split("]", 1)[0]
        # DRC descriptions prefix net names with '/'; the board may or may not
        # store the slash as part of the actual net name. Try both forms.
        codes = {c for c in (names.get(net), names.get(net.lstrip("/")), names.get("/" + net.lstrip("/"))) if c is not None}
        layer = None
        for ln, lid in LayerToId.items():
            if ln in desc:
                layer = lid
        if layer is None:
            print("SKIP", desc)
            continue
        mm = float(desc.split("length ")[1].split(" mm")[0])
        want = int(round(mm * 1e6))
        best = None
        for t in board.GetTracks():
            if t.Type() != pcbnew.PCB_TRACE_T:
                continue
            if t.GetNetCode() not in codes or t.GetLayer() != layer:
                continue
            if abs(int(abs(t.GetLength())) - want) <= 1000:  # 1 um
                best = t
                break
        if best is None:
            print("NOT FOUND", desc)
            continue
        if not DRY:
            board.Remove(best)
        removed += 1

print("removed", removed)
if removed and not DRY:
    board.Save(board_path)
    print("saved")
