#!/usr/bin/env python3
"""Stitch disconnected same-layer GND pour islands with vias to the other layer.

After an SES import, cleared corridors can split a GND pour into islands that
are not joined on their own layer (DRC reports zone-vs-zone unconnected pairs
all citing the same zone on one layer). For every filled-island without an
existing GND via, place one collision-checked GND via (on F.Cu islands ->
joining through the B.Cu pour, and vice versa), refill, and save.

Idempotent: a second dry run must place zero vias.

Usage (KiCad 9 container): stitch_pour_islands.py <board.kicad_pcb> [--dry]
"""
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path = sys.argv[1]
NM = 1e6
VIA_SIZE = 600000
VIA_DRILL = 300000
CLEAR = 200000

board = pcbnew.LoadBoard(board_path)
gnd = board.FindNet("/GND")
if gnd is None:
    print("no /GND net")
    sys.exit(1)
gnd_code = gnd.GetNetCode()

OUTLINE = pcbnew.VECTOR2I(96000000, 76000000)  # board 96x76 mm (Edge.Cuts probe)
EDGE_CLEAR = 500000

layers = [pcbnew.F_Cu, pcbnew.B_Cu]

via_pts = set()
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        via_pts.add((t.GetStart().x, t.GetStart().y))


def collides(pt, layer, netcode):
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            try:
                vw = t.GetSize()
            except Exception:
                vw = 600000
            for lp in (t.GetStart(), t.GetEnd()):
                import math
                d = math.hypot(lp.x - pt.x, lp.y - pt.y)
                if d < (VIA_SIZE / 2 + vw / 2 + CLEAR):
                    if t.GetNetCode() != netcode:
                        return True
        else:
            if t.GetLayer() != layer:
                continue
            r = VIA_SIZE / 2 + t.GetWidth() / 2 + CLEAR
            x1, x2 = sorted((t.GetStart().x, t.GetEnd().x))
            y1, y2 = sorted((t.GetStart().y, t.GetEnd().y))
            if x1 - r <= pt.x <= x2 + r and y1 - r <= pt.y <= y2 + r:
                if t.GetNetCode() != netcode:
                    return True
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == netcode:
                continue
            if not pad.IsOnLayer(layer):
                continue
            bb = pad.GetBoundingBox()
            r = VIA_SIZE / 2 + CLEAR
            if bb.GetX() - r <= pt.x <= bb.GetRight() + r and bb.GetY() - r <= pt.y <= bb.GetBottom() + r:
                return True
    return False


placed = 0
island_left = 0
for z in board.Zones():
    if z.GetNetname() != "/GND":
        continue
    for L in layers:
        if not z.HasFilledPolysForLayer(L):
            continue
        ps = z.GetFilledPolysList(L)
        n = ps.OutlineCount()
        print("zone fill layer", "F.Cu" if L == pcbnew.F_Cu else "B.Cu", "islands", n)
        for i in range(n):
            ol = ps.Outline(i)
            bb = ps.BBox(i)
            area = abs(ol.Area()) / 1e12
            if area < 0.05:
                continue
            # skip islands that already contain a GND via (idempotency)
            has_gnd_via = False
            for t in board.GetTracks():
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetCode() == gnd_code:
                    if ol.PointInside(t.GetStart()):
                        has_gnd_via = True
                        break
            if has_gnd_via:
                continue
            cx = int((bb.GetX() + bb.GetRight()) / 2)
            cy = int((bb.GetY() + bb.GetBottom()) / 2)
            found = None
            step = 200000
            ring = 0
            while ring < 300 and found is None:
                for dx in range(-ring, ring + 1):
                    for dy in range(-ring, ring + 1):
                        if max(abs(dx), abs(dy)) != ring:
                            continue
                        pt = pcbnew.VECTOR2I(cx + dx * step, cy + dy * step)
                        if pt.x < EDGE_CLEAR or pt.y < EDGE_CLEAR or pt.x > OUTLINE.x - EDGE_CLEAR or pt.y > OUTLINE.y - EDGE_CLEAR:
                            continue
                        if not ol.PointInside(pt):
                            continue
                        if (pt.x, pt.y) in via_pts or collides(pt, L, gnd_code):
                            continue
                        found = pt
                        break
                    if found:
                        break
                ring += 1
            if found is None:
                island_left += 1
                print("LEFT island", i, "layer", "F.Cu" if L == pcbnew.F_Cu else "B.Cu",
                      "area_mm2", round(area, 2),
                      "bbox", round(bb.GetX() / NM, 1), round(bb.GetY() / NM, 1),
                      round(bb.GetRight() / NM, 1), round(bb.GetBottom() / NM, 1))
                continue
            if not DRY:
                via = pcbnew.PCB_VIA(board)
                via.SetNet(gnd)
                via.SetWidth(VIA_SIZE)
                via.SetDrill(VIA_DRILL)
                via.SetPosition(found)
                board.Add(via)
                via_pts.add((found.x, found.y))
            placed += 1
            print("stitch", "F.Cu" if L == pcbnew.F_Cu else "B.Cu", "island", i,
                  "area_mm2", round(area, 2), "via @", round(found.x / NM, 2), round(found.y / NM, 2))

print("placed", placed, "left", island_left)
if placed and not DRY:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    board.Save(board_path)
    print("saved")
