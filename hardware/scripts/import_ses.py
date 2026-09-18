#!/usr/bin/env python3
"""Import a Specctra SES session and report route completeness.

Usage: import_ses.py <board.kicad_pcb> <session.ses>
Saves the board in place with the imported tracks/vias, then reports
track count, via count, and remaining unconnected pads via ratsnest.
"""
import sys

import pcbnew

board_path, ses_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)
ok = pcbnew.ImportSpecctraSES(board, ses_path)
print("ses_import", ok)
if not ok:
    sys.exit(1)
tracks = [t for t in board.GetTracks()]
vias = [t for t in tracks if t.Type() == pcbnew.PCB_VIA_T]
segs = [t for t in tracks if t.Type() == pcbnew.PCB_TRACE_T]
print("tracks", len(segs), "vias", len(vias))
board.Save(board_path)
print("saved", board_path)
# ratsnest (unconnected) count via a fresh load of the saved board
board2 = pcbnew.LoadBoard(board_path)
conn = board2.GetConnectivity()
try:
    conn.BuildRatsnest4()
    print("unconnected_lines", conn.GetUnconnectedLinesCount(board2.GetFatherOfItems().get_root(), 0, True))
except Exception as e:
    print("ratsnest probe failed:", e)
