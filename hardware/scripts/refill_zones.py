#!/usr/bin/env python3
"""Refill all copper zones on a board and report filled area per zone.

Usage (KiCad 9 container): refill_zones.py <board.kicad_pcb>
"""
import sys

import pcbnew

board_path = sys.argv[1]
board = pcbnew.LoadBoard(board_path)
zones = list(board.Zones())
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(zones)
board.Save(board_path)
board2 = pcbnew.LoadBoard(board_path)
for z in board2.Zones():
    print("zone", z.GetNetname() or "<rule-area>", "filled_mm2", round(z.GetFilledArea() / 1e6, 1))
print("saved", board_path)
