#!/usr/bin/env python3
"""Stitch disconnected same-layer GND pour islands with vias (v2).

A stitch via must fit fully inside the island: candidate points are tested
with an 8-point probe at 0.42 mm around the center (via radius 0.30 + 0.12
margin), so the via annulus cannot spill across the pour edge into the
clearance void around foreign copper (that spill caused the clearance/short
errors in v1). Points are also rejected if inside any same-layer GND pad
bbox or within 0.55 mm of any existing via of another net.

Usage (KiCad 9 container): stitch_pour_islands2.py <board.kicad_pcb> [--dry]
"""
import math
import sys

import pcbnew

DRY = "--dry" in sys.argv
board_path = sys.argv[1]
NM = 1e6
VIA_SIZE = 600000
VIA_DRILL = 300000
MARGIN = 420000  # probe radius: via 0.30 + 0.12 slack
BOARD_W, BOARD_H = 96000000, 76000000
EDGE_CLEAR = 500000

board = pcbnew.LoadBoard(board_path)
gnd = board.FindNet("/GND")
if gnd is None:
    print("no /GND net")
    sys.exit(1)
gnd_code = gnd.GetNetCode()
layers = [pcbnew.F_Cu, pcbnew.B_Cu]

via_pts = []  # (x,y,size,netcode)
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        try:
            s = t.GetSize()
        except Exception:
            s = 600000
        via_pts.append((t.GetStart().x, t.GetStart().y, s, t.GetNetCode()))

# GND pads per layer (merged copper that islands can contain)
gnd_pads = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        if pad.GetNetCode() == gnd_code:
            for L in layers:
                if pad.IsOnLayer(L):
                    gnd_pads[L].append(pad.GetBoundingBox())


def probes(pt):
    r = MARGIN
    return [pt,
            pcbnew.VECTOR2I(pt.x + r, pt.y), pcbnew.VECTOR2I(pt.x - r, pt.y),
            pcbnew.VECTOR2I(pt.x, pt.y + r), pcbnew.VECTOR2I(pt.x, pt.y - r),
            pcbnew.VECTOR2I(pt.x + r, pt.y + r), pcbnew.VECTOR2I(pt.x - r, pt.y - r),
            pcbnew.VECTOR2I(pt.x + r, pt.y - r), pcbnew.VECTOR2I(pt.x - r, pt.y + r)]


def ok(pt, ol, L, other):
    if pt.x < EDGE_CLEAR or pt.y < EDGE_CLEAR or pt.x > BOARD_W - EDGE_CLEAR or pt.y > BOARD_H - EDGE_CLEAR:
        return False
    for p in probes(pt):
        if not ol.PointInside(p):
            return False
    for bb in gnd_pads[L]:
        if bb.GetX() <= pt.x <= bb.GetRight() and bb.GetY() <= pt.y <= bb.GetBottom():
            return False
    # the via ring (r = VIA_SIZE/2 + clearance) must clear foreign copper on
    # BOTH layers: on L the pour voids already enforce this only against the
    # pour rule (0.25), but FR left tracks inside island footprints on the
    # opposite layer at plain 0.2 clearance.
    need = VIA_SIZE / 2 + 200000
    for (x1, y1, x2, y2, tw, tn, lay) in foreign_segs:
        if lay != other or tn == gnd_code:
            continue
        r = need + tw / 2
        # segment-vs-point distance
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            d = math.hypot(pt.x - x1, pt.y - y1)
        else:
            t = max(0, min(1, ((pt.x - x1) * dx + (pt.y - y1) * dy) / (dx * dx + dy * dy)))
            d = math.hypot(pt.x - (x1 + t * dx), pt.y - (y1 + t * dy))
        if d < r:
            return False
    for (vx, vy, vs, vn) in via_pts:
        if vn == gnd_code:
            continue
        if math.hypot(pt.x - vx, pt.y - vy) < need + vs / 2:
            return False
    for (px, py, pr, pn, play) in foreign_pads:
        if pn == gnd_code or play not in (L, other, -1):
            continue
        if math.hypot(pt.x - px, pt.y - py) < need + pr:
            return False
    return True


placed = 0
left = 0
for z in board.Zones():
    if z.GetNetname() != "/GND":
        continue
    for L in layers:
        if not z.HasFilledPolysForLayer(L):
            continue
        ps = z.GetFilledPolysList(L)
        n = ps.OutlineCount()
        lname = "F.Cu" if L == pcbnew.F_Cu else "B.Cu"
        print("zone fill layer", lname, "islands", n)
        for i in range(n):
            ol = ps.Outline(i)
            bb = ps.BBox(i)
            area = abs(ol.Area()) / 1e12
            if area < 0.05:
                continue
            if any(t.GetNetCode() == gnd_code and ol.PointInside(t.GetStart())
                   for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T):
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
                        if ok(pt, ol, L):
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
