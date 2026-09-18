#!/usr/bin/env python3
"""Remove tracks/vias whose UUID is not in the keep list (or only in a drop list).

Usage: drop_vias.py <board.kicad_pcb> uuid [uuid ...]
"""
import sys

import pcbnew

board_path = sys.argv[1]
drop = set(sys.argv[2:])
board = pcbnew.LoadBoard(board_path)
removed = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T and t.GetUUID().AsString() in drop:
        board.Remove(t)
        removed += 1
print("removed", removed)
if removed:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    board.Save(board_path)
    print("saved")
