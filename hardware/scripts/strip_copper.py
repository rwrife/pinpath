#!/usr/bin/env python3
"""Strip all tracks and vias from a board (keep zones, footprints, silk).

Usage: strip_copper.py <board.kicad_pcb>
Saves in place. Used to give the autorouter a fresh 2-layer canvas while
preserving placement and copper pours.
"""
import sys

import pcbnew

board_path = sys.argv[1]
board = pcbnew.LoadBoard(board_path)
removed_tracks = 0
removed_vias = 0
for t in list(board.GetTracks()):
    if t.Type() == pcbnew.PCB_VIA_T:
        removed_vias += 1
    else:
        removed_tracks += 1
    board.Remove(t)
board.Save(board_path)
print("removed_tracks", removed_tracks, "removed_vias", removed_vias)
