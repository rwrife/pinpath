#!/usr/bin/env python3
"""Bounded silk-text hygiene pass for issue #4 final board (pitfall 26 recipe).

Shrinks oversized Reference fields on TP*/SW* footprints and moves the
'DE-ENERGIZED CABLES ONLY' banner clear of dense silk. Adjudication is a
re-DRC outside this script; keep only if warning counts drop.
Usage: final_silk_fix.py <board> [banner_dy_mm]
"""
import sys
import pcbnew

board_path = sys.argv[1]
banner_dy = int(float(sys.argv[2]) * 1e6) if len(sys.argv) > 2 else 6_000_000
board = pcbnew.LoadBoard(board_path)

SMALL = pcbnew.VECTOR2I(800000, 800000)
THICK = 150000

shrunk = 0
for fp in board.Footprints():
    field = None
    for f in fp.GetFields():
        try:
            if f.GetFieldName() == "Reference" or f.GetId() == pcbnew.REFERENCE_FIELD:
                field = f
                break
        except AttributeError:
            continue
    if field is None:
        continue
    size = field.GetTextSize()
    if size.x > 800000 or size.y > 800000 or field.GetTextWidth() > THICK:
        field.SetTextSize(SMALL)
        field.SetTextThickness(THICK)
        shrunk += 1

moved = 0
for t in board.GetDrawings():
    if t.Type() in (pcbnew.PCB_TEXT_T, pcbnew.PCB_TEXT) and "Silk" in t.GetLayerName():
        if "DE-ENERGIZED" in t.GetText():
            pos = t.GetTextPos()
            t.SetTextPos(pcbnew.VECTOR2I(pos.x, pos.y - banner_dy))
            moved += 1

print("shrunk:", shrunk, "banner moved:", moved)
board.Save(board_path)
print("saved")
