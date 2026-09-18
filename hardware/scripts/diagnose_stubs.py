#!/usr/bin/env python3
"""Diagnose why close_stubs_xlayer rejects each remaining DRC unconnected pair.

For each pair, rebuild the three candidate routes and report the FIRST
colliding foreign object (net + description) for each rejected candidate.

Usage (KiCad 9 container): diagnose_stubs.py <board.kicad_pcb> <drc.json>
"""
import json
import math
import re
import sys

import pcbnew

STUB_W = 150000
VIA_SIZE = 600000
CLEAR = 200000
HEAD = 20000
NM = 1e6

board_path, drc_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)
LAYER_NAME = {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu"}


def capsule(p1, p2, r):
    dx, dy = p2.x - p1.x, p2.y - p1.y
    ln = math.hypot(dx, dy) or 1
    px, py = -dy / ln * r, dx / ln * r
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for q in ((p1.x + px, p1.y + py), (p2.x + px, p2.y + py),
              (p2.x - px, p2.y - py), (p1.x - px, p1.y - py)):
        ch.Append(int(q[0]), int(q[1]), True)
    ch.Append(int(p1.x + px), int(p1.y + py))
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


def ring(p, r):
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for k in range(12):
        a = 2 * math.pi * k / 12
        ch.Append(int(p.x + r * math.cos(a)), int(p.y + r * math.sin(a)), True)
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


SEG_R = STUB_W / 2 + CLEAR + HEAD
RING_R = VIA_SIZE / 2 + CLEAR + HEAD


def first_hit(shape, layer, netcode, exempt_ids):
    for t in board.GetTracks():
        if t.GetNetCode() == netcode or id(t) in exempt_ids:
            continue
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() != layer:
            continue
        if shape.Collide(t.GetEffectiveShape(layer), 0):
            d = ("via " if t.Type() == pcbnew.PCB_VIA_T else "track ") + t.GetNetname()
            p = t.GetStart() if t.Type() == pcbnew.PCB_TRACE_T else t.GetPosition()
            return f"{d} @({p.x/1e6:.2f},{p.y/1e6:.2f})"
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == netcode or id(pad) in exempt_ids:
                continue
            if not pad.IsOnLayer(layer):
                continue
            if shape.Collide(pad.GetEffectiveShape(layer), 0):
                p = pad.GetPosition()
                return f"pad {fp.GetReference()}.{pad.GetPadName()} [{pad.GetNetname()}] @({p.x/1e6:.2f},{p.y/1e6:.2f})"
    return None


pat_end = re.compile(r"^Track \[/(.*?)\] on ([FB])\.Cu, length")
pat_via = re.compile(r"^(?:Blind/Buried )?Via \[/(.*?)\] on \S+")
pat_pad = re.compile(r"^(?:SMD |PTH )?[Pp]ad (\S+) \[/(.*?)\] of (\S+)(?: on ([FB])\.Cu)?$")

pads_by = {}
for fp in board.GetFootprints():
    for pad in fp.Pads():
        pads_by[(fp.GetReference(), pad.GetPadName())] = pad


def V(pos):
    return pcbnew.VECTOR2I(int(pos["x"] * NM), int(pos["y"] * NM))


def anchor(desc, pos):
    m = pat_end.match(desc)
    if m:
        lay = pcbnew.F_Cu if m.group(2) == "F" else pcbnew.B_Cu
        p = V(pos)
        tkey = None
        for t in board.GetTracks():
            if t.Type() != pcbnew.PCB_TRACE_T or t.GetLayer() != lay:
                continue
            if t.GetNetname().lstrip("/") != m.group(1):
                continue
            for end in (t.GetStart(), t.GetEnd()):
                if abs(end.x - p.x) < 30000 and abs(end.y - p.y) < 30000:
                    tkey = t
        return {"kind": "track", "pos": p, "layers": [lay], "exempt": [tkey] if tkey else []}
    m = pat_via.match(desc)
    if m:
        p = V(pos)
        return {"kind": "via", "pos": p, "layers": None, "exempt": []}
    m = pat_pad.match(desc)
    if m:
        pad = pads_by.get((m.group(3), m.group(1)))
        if pad is None:
            return None
        return {"kind": "pad", "pos": pad.GetPosition(),
                "layers": [pcbnew.F_Cu if pad.GetLayer() == pcbnew.F_Cu else pcbnew.B_Cu],
                "exempt": [pad]}
    return None


for item in json.load(open(drc_path))["unconnected_items"]:
    ia, ib = item["items"]
    A = anchor(ia["description"], ia.get("pos") or ib.get("pos"))
    B = anchor(ib["description"], ib.get("pos") or ia.get("pos"))
    if A is None or B is None:
        continue
    net = pat_end.match(ia["description"]) or pat_end.match(ib["description"]) or pat_via.match(ia["description"]) or pat_pad.match(ia["description"])
    netname = net.group(1) if net and net.groups else "?"
    nobj = board.FindNet("/" + netname)
    if nobj is None:
        continue
    netcode = nobj.GetNetCode()
    exempt_ids = {id(e) for e in A["exempt"] + B["exempt"] if e is not None}
    pA, pB = A["pos"], B["pos"]
    print(f"\n== {ia['description']} | {ib['description']}")
    print(f"   A@({pA.x/1e6:.2f},{pA.y/1e6:.2f}) B@({pB.x/1e6:.2f},{pB.y/1e6:.2f})")
    lays = []
    if A["layers"] and B["layers"] and A["layers"][0] == B["layers"][0]:
        lays = [A["layers"][0]]
    elif A["layers"] is None or B["layers"] is None:
        lays = [pcbnew.F_Cu, pcbnew.B_Cu]
    elif A["layers"][0] == B["layers"][0]:
        lays = A["layers"]
    for lay in lays:
        h = first_hit(capsule(pA, pB, SEG_R), lay, netcode, exempt_ids)
        print(f"   straight {LAYER_NAME[lay]}: {'OK' if h is None else h}")
    # xlayer both directions
    for src, dst in ((A, B), (B, A)):
        if not src["layers"]:
            continue
        h = first_hit(capsule(src["pos"], dst["pos"], SEG_R), src["layers"][0], netcode, exempt_ids)
        hr = None
        for l2 in (pcbnew.F_Cu, pcbnew.B_Cu):
            hr = first_hit(ring(dst["pos"], RING_R), l2, netcode, exempt_ids)
            if hr:
                break
        print(f"   xseg {LAYER_NAME[src['layers'][0]]}: {'OK' if h is None else h} | ring@dst: {'OK' if hr is None else hr}")
    if A["layers"] and B["layers"]:
        for elbow in (pcbnew.VECTOR2I(pA.x, pB.y), pcbnew.VECTOR2I(pB.x, pA.y)):
            ok = True
            notes = []
            if first_hit(ring(elbow, RING_R), pcbnew.F_Cu, netcode, exempt_ids) or first_hit(ring(elbow, RING_R), pcbnew.B_Cu, netcode, exempt_ids):
                ok = False
                notes.append("ring")
            h1 = first_hit(capsule(pA, elbow, SEG_R), A["layers"][0], netcode, exempt_ids)
            if h1:
                ok = False
                notes.append(f"seg1:{h1}")
            h2 = first_hit(capsule(elbow, pB, SEG_R), B["layers"][0], netcode, exempt_ids)
            if h2:
                ok = False
                notes.append(f"seg2:{h2}")
            print(f"   L-elbow ({elbow.x/1e6:.2f},{elbow.y/1e6:.2f}): {'OK' if ok else ';'.join(notes)}")
