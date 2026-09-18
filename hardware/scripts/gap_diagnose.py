#!/usr/bin/env python3
"""Diagnose what foreign copper sits inside each unresolved stub gap.

For each DRC unconnected pair, draws the rectangle spanning the two anchors
(expanded slightly) and lists all foreign-net pads and tracks whose shapes
enter it, with their clearance to the straight segment between anchors.

Usage: python3 gap_diagnose.py <board.kicad_pcb> <drc.json>
"""
import json
import math
import sys

import pcbnew

NM = 1e6
board_path, drc_path = sys.argv[1], sys.argv[2]
drc = json.load(open(drc_path))
board = pcbnew.LoadBoard(board_path)

all_pads = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        all_pads.append((fp.GetReference(), p))
tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]


def resolve(desc, x, y):
    """Return (net, anchor_nm, kind)."""
    import re

    m = re.search(r"Pad (\S+) \[([^\]]*)\] of (\S+)", desc)
    if m:
        pin, ref = m.group(1), m.group(3)
        best = None
        for r, p in all_pads:
            if r == ref and p.GetPadName() == pin:
                d = math.hypot(p.GetPosition().x / NM - x, p.GetPosition().y / NM - y)
                if best is None or d < best[0]:
                    best = (d, p)
        if best:
            return best[1].GetNetname(), best[1].GetPosition(), "pad"
        return None
    if desc.startswith("Track") or desc.startswith("Via"):
        typ = pcbnew.PCB_VIA_T if desc.startswith("Via") else pcbnew.PCB_TRACE_T
        net = re.search(r"\[([^\]]*)\]", desc).group(1)
        best = None
        for t in board.GetTracks():
            if t.Type() != typ:
                continue
            if t.GetNetname() != net:
                continue
            pts = (
                (t.GetStart(), t.GetEnd())
                if typ == pcbnew.PCB_TRACE_T
                else (t.GetStart(),)
            )
            for pt in pts:
                d = math.hypot(pt.x / NM - x, pt.y / NM - y)
                if best is None or d < best[0]:
                    best = (d, pt)
        if best:
            return net, best[1], "track"
    return None


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


for item in drc["unconnected_items"]:
    ia, ib = item["items"]
    ra = resolve(ia["description"], ia["pos"]["x"], ia["pos"]["y"])
    rb = resolve(ib["description"], ib["pos"]["x"], ib["pos"]["y"])
    if not ra or not rb:
        print("UNRESOLVED:", ia["description"], "<->", ib["description"])
        continue
    net = ra[0]
    (ax, ay), (bx, by) = ra[1], rb[1]
    pad_ref = ia["description"].split(" of ")[-1]
    blockers = []
    for ref, p in all_pads:
        if p.GetNetname() == net:
            continue
        px, py = p.GetPosition()
        d = seg_dist(px / NM, py / NM, ax / NM, ay / NM, bx / NM, by / NM)
        # rough: pad size/2 + half-width 0.075 + clearance 0.2
        half = max(p.GetSize().x, p.GetSize().y) / 2 / NM
        if d - half < 0.30:
            blockers.append(f"pad {ref}:{p.GetPadName()}({p.GetNetname()}) d={d:.3f}")
    for t in tracks:
        if t.GetNetname() == net:
            continue
        d = min(
            seg_dist(q.x / NM, q.y / NM, ax / NM, ay / NM, bx / NM, by / NM)
            for q in (t.GetStart(), t.GetEnd())
        )
        dd = min(
            seg_dist(
                (t.GetStart().x + t.GetEnd().x) / 2 / NM,
                (t.GetStart().y + t.GetEnd().y) / 2 / NM,
                ax / NM,
                ay / NM,
                bx / NM,
                by / NM,
            ),
            d,
        )
        if dd - (t.GetWidth() / 2 / NM) < 0.30:
            blockers.append(
                f"trk({t.GetNetname()},{t.GetWidth()/NM:.2f}w) d={dd:.3f} @({t.GetStart().x/NM:.1f},{t.GetStart().y/NM:.1f})-({t.GetEnd().x/NM:.1f},{t.GetEnd().y/NM:.1f}) {t.GetLayerName()}"
            )
    gap = math.hypot((bx - ax) / NM, (by - ay) / NM)
    print(
        f"\nNET {net}  gap {gap:.2f} mm  {ia['description']} <-> {ib['description']}"
    )
    for b in blockers[:8]:
        print("   BLOCK:", b)
