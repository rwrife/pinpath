#!/usr/bin/env python3
"""Report courtyard overlaps and board-edge clearance for a board.

Run inside the KiCad 9 runtime image (parts-tally-kicad:9-arm64):
    python3 check_courtyards.py <board.kicad_pcb>

Per footprint, unions the axis-aligned bounds of its courtyard graphics
(F.CrtYd or B.CrtYd depending on the footprint layer); footprints without a
courtyard fall back to their pad bbox. Pairwise rectangle overlap is
reported with overlap extents, and every courtyard is checked against the
Edge.Cuts outline bbox. This mirrors how KiCad courtyard DRC treats typical
rectangular courtyards; a naive whole-footprint bbox (which includes
courtyard, pads, and reference text on all layers) over-reports heavily in
dense designs, so it is not used here.

This is a placement inspection aid for issue #4 review — `kicad-cli pcb drc`
remains the authoritative rule check.
"""
import re
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
NM = 1e6

data = []
for fp in board.GetFootprints():
    layer = str(fp.GetLayerName())
    crt_layer = "CrtYd"
    side = "B." if layer.startswith("B.") else "F."
    xs, ys = [], []
    for item in fp.GraphicalItems():
        ln = str(item.GetLayerName())
        if crt_layer in ln and ln.startswith(side):
            try:
                pts = item.GetEffectiveShape().CPoints()
            except Exception:
                pts = None
            if pts:
                for p in pts:
                    xs.append(p.x)
                    ys.append(p.y)
            else:
                box = item.GetBoundingBox()
                xs += [box.GetX(), box.GetX() + box.GetWidth()]
                ys += [box.GetY(), box.GetY() + box.GetHeight()]
    if not xs:  # no courtyard: pad bbox fallback
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            xs += [box.GetX(), box.GetX() + box.GetWidth()]
            ys += [box.GetY(), box.GetY() + box.GetHeight()]
    if not xs:
        continue
    data.append((fp.GetReference(), (min(xs), min(ys), max(xs), max(ys))))

overlaps = []
for i in range(len(data)):
    r1, (a1, b1, a2, b2) = data[i]
    for j in range(i + 1, len(data)):
        r2, (c1, d1, c2, d2) = data[j]
        ox = min(a2, c2) - max(a1, c1)
        oy = min(b2, d2) - max(b1, d1)
        if ox > 0 and oy > 0:
            overlaps.append((r1, r2, ox / NM, oy / NM))

import os

txt = open(sys.argv[1]).read()
segs = re.findall(
    r'\(gr_line\s*\(start ([-\d.]+) ([-\d.]+)\)\s*\(end ([-\d.]+) ([-\d.]+)\).*?\(layer "Edge\.Cuts"\)',
    txt,
    re.S,
)
edge = None
if segs:
    xs, ys = [], []
    for s in segs:
        xs += [float(s[0]), float(s[2])]
        ys += [float(s[1]), float(s[3])]
    edge = (min(xs), min(ys), max(xs), max(ys))

edge_issues = []
if edge:
    for ref, (x1, y1, x2, y2) in data:
        if (
            x1 / NM < edge[0]
            or y1 / NM < edge[1]
            or x2 / NM > edge[2]
            or y2 / NM > edge[3]
        ):
            edge_issues.append(ref)

print(f"footprints measured: {len(data)}")
if edge:
    print(
        f"board outline mm: {edge[0]:.2f},{edge[1]:.2f} .. "
        f"{edge[2]:.2f},{edge[3]:.2f}  ({len(segs)} Edge.Cuts lines)"
    )
print(f"courtyard overlaps: {len(overlaps)}")
for r1, r2, ox, oy in overlaps[:80]:
    print(f"  {r1} <-> {r2}: {ox:.3f} x {oy:.3f} mm")
print(f"edge clearance violations: {len(edge_issues)} {edge_issues[:20]}")
sys.exit(0 if not overlaps and not edge_issues else 1)
