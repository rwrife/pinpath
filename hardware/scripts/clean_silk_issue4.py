#!/usr/bin/env python3
"""Silkscreen cleanup for pinpath rev-A candidate (issue #4).

Run inside KiCad 9 pcbnew (parts-tally-kicad:9-arm64):
    python3 clean_silk_issue4.py <board.kicad_pcb>

Policy (documented in hardware/layout-notes.md):
- Dense scan-lane parts (D*, R*, C*) sit at pitches where the default 1 mm
  reference silkscreen overruns neighbouring copper, producing
  silk_over_copper / silk_overlap DRC warnings. Hide the Reference field
  silkscreen on those parts only; their position is unambiguous from the
  assembly drawing + BOM (and they carry no user-serviceable identity).
- Keep visible: U*, J*, SW1, H*, TP* and all bank/pin-1 board graphics.
- Raise standalone silkscreen graphic text thickness to 0.15 mm to satisfy
  the text_thickness rule (fab minimum).
"""
import re
import sys

import pcbnew

path = sys.argv[1]
board = pcbnew.LoadBoard(path)

DENSE = re.compile(r"^[DRC]\d+$")

hidden = 0
for f in board.GetFootprints():
    ref = f.GetReference()
    if not ref or not DENSE.match(ref):
        continue
    for fx in f.GetFields():
        if fx.GetName() == "Reference":
            fx.SetVisible(False)
            hidden += 1

thick = 0
for item in board.GetDrawings():
    if item.Type() == pcbnew.PCB_TEXT_T and "Silk" in item.GetLayerName():
        for setter in ("SetTextWidth", "SetTextThickness"):
            try:
                if getattr(item, "Get" + setter[3:])() < 150000:
                    getattr(item, setter)(150000)
                    thick += 1
            except Exception:
                pass

board.Save(path)
print(f"hidden_refs {hidden} fixed_thickness {thick}")
