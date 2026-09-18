#!/usr/bin/env python3
"""Stitch disconnected same-layer GND pour islands with vias (v3).

A stitch via must fit, with its full annulus plus clearance (probe radius
0.50 mm = via 0.30 + 0.20), entirely inside the island on its layer AND
inside the GND pour fill of the OPPOSITE layer (otherwise it shorts foreign
copper the opposite pour does not cover). GND pads are same-net merges;
non-GND pads on either layer are excluded explicitly.

Usage (KiCad 9 container): stitch_pour_islands3.py <board.kicad_pcb> [--dry]
"""
import math
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path = sys.argv[1]
NM = 1e6
VIA_SIZE = 600000
VIA_DRILL = 300000
MARGIN = 500000  # via radius 0.30 + clearance 0.20
BOARD_W, BOARD_H = 96000000, 76000000
EDGE_CLEAR = 500000

board = pcbnew.LoadBoard(board_path)
gnd = board.FindNet("/GND")
if gnd is None:
    print("no /GND net")
    sys.exit(1)
gnd_code = gnd.GetNetCode()
layers = [pcbnew.F_Cu, pcbnew.B_Cu]

via_pts = []
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        try:
            s = t.GetSize()
        except Exception:
            s = 600000
        via_pts.append((t.GetStart().x, t.GetStart().y, s, t.GetNetCode()))

foreign_pads = []  # (x,y,approx_r,netcode)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetCode() == gnd_code:
            continue
        bb = pad.GetBoundingBox()
        foreign_pads.append(((bb.GetX() + bb.GetRight()) // 2, (bb.GetY() + bb.GetBottom()) // 2,
                             max(bb.GetWidth(), bb.GetHeight()) // 2, pad.GetNetCode()))

gnd_polys = {}
for z in board.Zones():
    if z.GetNetname() != "/GND":
        continue
    for L in layers:
        if z.HasFilledPolysForLayer(L):
            gnd_polys[L] = z.GetFilledPolysList(L)


def in_any(polyset, pt):
    for i in range(polyset.OutlineCount()):
        if polyset.Outline(i).PointInside(pt):
            return True
    return False


def probes(pt):
    r = MARGIN
    return [pt,
            pcbnew.VECTOR2I(pt.x + r, pt.y), pcbnew.VECTOR2I(pt.x - r, pt.y),
            pcbnew.VECTOR2I(pt.x, pt.y + r), pcbnew.VECTOR2I(pt.x, pt.y - r),
            pcbnew.VECTOR2I(pt.x + r, pt.y + r), pcbnew.VECTOR2I(pt.x - r, pt.y - r),
            pcbnew.VECTOR2I(pt.x + r, pt.y - r), pcbnew.VECTOR2I(pt.x - r, pt.y + r)]


def ok(pt, island, other_ps):
    if pt.x < EDGE_CLEAR or pt.y < EDGE_CLEAR or pt.x > BOARD_W - EDGE_CLEAR or pt.y > BOARD_H - EDGE_CLEAR:
        return False
    for p in probes(pt):
        if not island.PointInside(p):
            return False
        if not in_any(other_ps, p):
            return False
    for (px, py, pr, pn) in foreign_pads:
        if math.hypot(pt.x - px, pt.y - py) < MARGIN + pr:
            return False
    for (vx, vy, vs, vn) in via_pts:
        if vn == gnd_code:
            continue
        if math.hypot(pt.x - vx, pt.y - vy) < MARGIN + vs / 2:
            return False
    return True


placed = 0
left = 0
for L in layers:
    lname = "F.Cu" if L == pcbnew.F_Cu else "B.Cu"
    other = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
    if L not in gnd_polys:
        continue
    ps = gnd_polys[L]
    n = ps.OutlineCount()
    print("layer", lname, "islands", n)
    for i in range(n):
        ol = ps.Outline(i)
        bb = ps.BBox(i)
        area = abs(ol.Area()) / 1e12
        if area < 0.05:
            continue
        if any(t.GetNetCode() == gnd_code and t.Type() == pcbnew.PCB_VIA_T and ol.PointInside(t.GetStart())
               for t in board.GetTracks()):
            continue
        cx = int((bb.GetX() + bb.GetRight()) / 2)
        cy = int((bb.GetY() + bb.GetBottom()) / 2)
        found = None
        step = 200000
        ring = 0
        while ring < 250 and found is None:
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) != ring:
                        continue
                    pt = pcbnew.VECTOR2I(cx + dx * step, cy + dy * step)
                    if ok(pt, ol, gnd_polys[other]):
                        found = pt
                        break
                if found:
                    break
            ring += 1
        if found is None:
            left += 1
            print("LEFT island", i, lname, "area_mm2", round(area, 2),
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
            via_pts.append((found.x, found.y, VIA_SIZE, gnd_code))
        placed += 1
        print("stitch", lname, "island", i, "area_mm2", round(area, 2),
              "via @", round(found.x / NM, 2), round(found.y / NM, 2))

print("placed", placed, "left", left)
if placed and not DRY:
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(list(board.Zones()))
    board.Save(board_path)
    print("saved")
