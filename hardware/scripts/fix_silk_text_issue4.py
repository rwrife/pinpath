#!/usr/bin/env python3
"""Fix silk graphic-text geometry (issue #4).

The initial relayout created board silk labels with an accidentally-flat
font size (0.8 x 0.15 mm), which makes the rendered stroke 0.0187 mm and
triggers text_thickness DRC. Normalize all standalone F.SilkS / B.SilkS
graphic text to 1.0 x 1.0 mm glyph size with 0.15 mm stroke.
"""
import sys

import pcbnew

path = sys.argv[1]
board = pcbnew.LoadBoard(path)
n = 0
for item in board.GetDrawings():
    if item.Type() == pcbnew.PCB_TEXT_T and "Silk" in item.GetLayerName():
        item.SetTextSize(pcbnew.VECTOR2I(1000000, 1000000))
        item.SetTextThickness(150000)
        n += 1
board.Save(path)
print("normalized_silk_text", n)
