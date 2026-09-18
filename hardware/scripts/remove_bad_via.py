#!/usr/bin/env python3
"""Remove one offending via (by coordinate) plus short same-net stubs touching it.

Usage (KiCad 9 container): remove_bad_via.py <board.kicad_pcb> <x_mm> <y_mm> [--dry]
Deletes every track whose endpoint coincides with the via on the via's net
and is shorter than 2 mm, then the via itself.
"""
import sys

import pcbnew

DRY = "--dry" in sys.argv
path = sys.argv[1]
x, y = int(float(sys.argv[2]) * 1e6), int(float(sys.argv[3]) * 1e6)
board = pcbnew.LoadBoard(path)

target = None
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T and t.GetPosition() == pcbnew.VECTOR2I(x, y):
        target = t
        break
if target is None:
    print("no via at", x / 1e3, y / 1e3)
    sys.exit(1)

net = target.GetNetCode()
pos = target.GetPosition()
removed = [target]
for t in list(board.GetTracks()):
    if t is target or t.Type() != pcbnew.PCB_TRACE_T or t.GetNetCode() != net:
        continue
    for end in (t.GetStart(), t.GetEnd()):
        d = end - pos
        if (d.x * d.x + d.y * d.y) < (10000 * 10000):  # 10 um
            if abs(t.GetLength()) < 2e6:  # 2 mm stub
                removed.append(t)
            break

print("net", target.GetNetname(), "removing", len(removed), "items")
if not DRY:
    for t in removed:
        board.Remove(t)
    board.Save(path)
    print("saved")
