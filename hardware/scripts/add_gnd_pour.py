#!/usr/bin/env python3
"""Add board-level GND copper pour (F.Cu + B.Cu) to the pinpath rev-A board.

Rationale (issue #4 acceptance: documented grounding and return paths):
- The rev-A carrier is a 2-layer board; signal return currents need a
  reference ground pour spanning the board on both layers.
- Existing keepout rule areas (USB cable clearance, TP probe keepouts) are
  raised to zone priority 1 so they carve the pour (pour stays priority 0).
- Pour net is /GND; thermal relief connects to every GND pad.

Run inside KiCad 9 (parts-tally-kicad:9-arm64):
    python3 add_gnd_pour.py <board.kicad_pcb>
The script fills zones with ZONE_FILLER and saves. Re-run kicad-cli pcb drc
afterwards to adjudicate; do not trust the fill call's own exit.
"""
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
NM = 1e6

# Skip if pour already present
for z in board.Zones():
    if z.GetNetname() == "/GND":
        print("GND pour already present; skipping")
        sys.exit(0)

gnd = board.FindNet("/GND")
if gnd is None:
    print("ERROR: /GND net not found")
    sys.exit(1)

# Raise existing rule-area (no-net) zones above the pour so they carve it.
raised = 0
for z in board.Zones():
    if z.GetNetname() == "":
        z.SetAssignedPriority(1)
        raised += 1
print("raised rule-area priorities:", raised)

outline = [(0, 0), (96 * NM, 0), (96 * NM, 76 * NM), (0, 76 * NM)]

for layer, name in ((pcbnew.F_Cu, "GND pour F.Cu"), (pcbnew.B_Cu, "GND pour B.Cu")):
    z = pcbnew.ZONE(board)
    z.SetNet(gnd)
    z.SetLayer(layer)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetLocalClearance(250000)  # 0.25 mm
    z.SetMinThickness(254000)  # 0.254 mm
    z.SetZoneName(name)
    poly = pcbnew.SHAPE_POLY_SET()
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in outline:
        ch.Append(int(x), int(y), True)
    ch.SetClosed(True)
    z.AddPolygon(ch)
    board.Add(z)
    print("added", name)

zones = list(board.Zones())
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(zones)
filled = [z.GetZoneName() for z in zones if z.IsFilled() or z.GetFilledArea() > 0]
print("zones with copper:", len(filled))
board.Save(sys.argv[1])
print("saved", sys.argv[1])

# reload probe
b2 = pcbnew.LoadBoard(sys.argv[1])
gnd_zones = [z for z in b2.Zones() if z.GetNetname() == "/GND"]
print("reload: GND zones =", len(gnd_zones), "areas mm2 =", [round(z.GetFilledArea() / (NM * NM), 1) for z in gnd_zones])
