#!/usr/bin/env python3
"""Third-pass silkscreen hygiene for the pinpath rev-A board (issue #4).

Targets the residual DRC silk warnings only, without removing any
functional label (test-point identity must stay probeable/attributable):
- Move board labels 'BANK A'/'BANK B' off the bank-entry resistor outlines
  and separate the 'DE-ENERGIZED CABLES ONLY' banner from 'PinPath rev-A'.
- Shrink the Reference silkscreen of the dense TP* cluster and SW1 to
  0.8 mm / 0.15 mm stroke so the text clears neighbouring copper/outlines.

Run inside KiCad 9 (parts-tally-kicad:9-arm64):
    python3 silk_fix_issue4_p3.py <board.kicad_pcb>
Then re-run kicad-cli pcb drc to measure the effect; residuals stay as
documented warnings (silkscreen cosmetics do not affect connectivity).
"""
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
NM = 1e6

SMALL = {
    "TP1", "TP2", "TP3", "TP4", "TP5", "TP6",
    "TP7", "TP8", "TP9", "TP10", "TP11", "TP12", "SW1",
}
shrunk = 0
for fp in board.GetFootprints():
    if fp.GetReference() in SMALL:
        for f in fp.GetFields():
            if f.GetName() == "Reference":
                f.SetVisible(True)
                f.SetTextSize(pcbnew.VECTOR2I(int(0.8 * NM), int(0.8 * NM)))
                f.SetTextThickness(150000)
                shrunk += 1
print("shrunk reference fields:", shrunk)

MOVED = {"BANK A": (0, -2.2), "BANK B": (0, -2.2), "DE-ENERGIZED CABLES ONLY": (0, -1.8)}
moved = 0
for item in board.GetDrawings():
    if "Silk" not in str(item.GetLayerName()):
        continue
    if type(item).__name__ not in ("PCB_TEXT", "PCB_TEXT_T", "BOARD_DESIGNATE"):
        continue
    txt = None
    try:
        txt = item.GetText()
    except Exception:
        continue
    if txt in MOVED:
        dx, dy = MOVED[txt]
        pos = item.GetPosition()
        item.SetPosition(pcbnew.VECTOR2I(pos.x + int(dx * NM), pos.y + int(dy * NM)))
        moved += 1
print("moved labels:", moved, "drawings scanned")

board.Save(sys.argv[1])
print("saved", sys.argv[1])
