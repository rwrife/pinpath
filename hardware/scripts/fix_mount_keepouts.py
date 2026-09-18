#!/usr/bin/env python3
"""Reposition the three misplaced mounting-hole keepout rings (issue #4).

The original rings were authored at footprint-local coordinates and landed
off-board for H2/H3/H4, leaving only H1's ring effective (pitfall 33).
Remove every rule-area zone and recreate square 6.2mm keepout pockets
centered on the actual hole centers, with the pitfall-33 flag set so the
hole pads themselves stay legal. Then refill GND pours.
Usage: fix_mount_keepouts.py <board>
"""
import pcbnew

BOARD = "pinpath.kicad_pcb"
HOLES = {"H1": (5.0, 5.0), "H2": (91.0, 44.0), "H3": (91.0, 71.0), "H4": (28.5, 70.5)}
SIDE = 6.2e6  # same footprint as the original rings
NM = 1e6

board = pcbnew.LoadBoard(BOARD)

# 1. drop existing rule-area zones
removed = 0
for z in list(board.Zones()):
    if z.GetIsRuleArea():
        board.Remove(z)
        removed += 1

# 2. recreate centered on true hole centers
gnd = board.FindNet("/GND") or board.FindNet("GND")
for ref, (cx, cy) in HOLES.items():
    x0, y0 = int((cx * NM) - SIDE / 2), int((cy * NM) - SIDE / 2)
    x1, y1 = x0 + int(SIDE), y0 + int(SIDE)
    z = pcbnew.ZONE(board)
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)):
        chain.Append(int(x), int(y), True)
    chain.SetClosed(True)
    z.AddPolygon(chain)
    z.SetIsRuleArea(True)
    z.SetAssignedPriority(1)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowFootprints(False)
    z.SetDoNotAllowCopperPour(True)
    z.SetNet(gnd)
    board.Add(z)
    print("ring", ref, "at", x0 / NM, y0 / NM, x1 / NM, y1 / NM)

# 3. refill pours + keepout carve-outs
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(list(board.Zones()))
board.Save(BOARD)
print("removed", removed, "old rings; added 4; refilled; saved")
