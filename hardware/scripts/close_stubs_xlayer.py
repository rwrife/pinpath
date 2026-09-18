#!/usr/bin/env python3
"""Cross-layer deterministic stub closer for pinpath rev-A (issue #4).

Reads KiCad DRC JSON `unconnected_items` pairs and closes them with
collision-checked copper:

* each cited item is normalized to an ANCHOR: a position, the layer(s) its
  copper occupies, and the object to exempt from collision tests
  (the pad / via / track the cited endpoint belongs to);
* same-layer pair  -> straight capsule, else L-route with an elbow via on
  the opposite layer (two elbow candidates);
* cross-layer pair -> straight segment on the anchor layer plus a joining
  via at the far endpoint (both layers ring-checked), or the mirror form.

Every candidate capsule/ring is tested against ALL foreign copper on the
layer at netclass clearance + headroom; nothing is written unless it passes.

Usage (KiCad 9 container): close_stubs_xlayer.py <board.kicad_pcb> <drc.json> [--dry]
"""
import json
import math
import re
import sys

import pcbnew

DRY = "--dry" in sys.argv
STUB_W = 150000
VIA_SIZE = 600000
VIA_DRILL = 300000
CLEAR = 200000
HEAD = 20000
NM = 1e6

board_path, drc_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)

LAYER_NAME = {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu"}
OTHER = {pcbnew.F_Cu: pcbnew.B_Cu, pcbnew.B_Cu: pcbnew.F_Cu}


def capsule(p1, p2, r):
    """Rectangle polygon around segment p1-p2 expanded by radius r."""
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
    n = 12
    for k in range(n):
        a = 2 * math.pi * k / n
        ch.Append(int(p.x + r * math.cos(a)), int(p.y + r * math.sin(a)), True)
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


SEG_R = STUB_W / 2 + CLEAR + HEAD
RING_R = VIA_SIZE / 2 + CLEAR + HEAD


def collides(shape, layer, netcode, exempt_ids):
    for t in board.GetTracks():
        if t.GetNetCode() == netcode or id(t) in exempt_ids:
            continue
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() != layer:
            continue
        if shape.Collide(t.GetEffectiveShape(layer), 0):
            return True
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == netcode or id(pad) in exempt_ids:
                continue
            if not pad.IsOnLayer(layer):
                continue
            if shape.Collide(pad.GetEffectiveShape(layer), 0):
                return True
    return False


def seg_ok(p1, p2, layer, netcode, exempt_ids):
    return not collides(capsule(p1, p2, SEG_R), layer, netcode, exempt_ids)


def via_ok(p, netcode, exempt_ids):
    for lay in (pcbnew.F_Cu, pcbnew.B_Cu):
        if collides(ring(p, RING_R), lay, netcode, exempt_ids):
            return False
    return True


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
    """-> dict(kind, pos, layers (list of copper layers or None for both), exempt list) or None."""
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
        return {"kind": "track", "net": m.group(1), "pos": p, "layers": [lay],
                "exempt": [tkey] if tkey else [], "found": tkey is not None}
    m = pat_via.match(desc)
    if m:
        p = V(pos)
        ex = None
        for t in board.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T and abs(t.GetPosition().x - p.x) < 30000 and abs(t.GetPosition().y - p.y) < 30000:
                ex = t
        return {"kind": "via", "net": m.group(1), "pos": p, "layers": None,
                "exempt": [ex] if ex else [], "found": True}
    m = pat_pad.match(desc)
    if m:
        pad = pads_by.get((m.group(3), m.group(1)))
        if pad is None:
            print("NO PAD", m.group(3), m.group(1))
            return None
        return {"kind": "pad", "net": m.group(2), "pos": pad.GetPosition(),
                "layers": [pcbnew.F_Cu if pad.GetLayer() == pcbnew.F_Cu else pcbnew.B_Cu],
                "exempt": [pad], "found": True}
    print("UNPARSED", desc)
    return None


def add_track(p1, p2, layer, netcode):
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(p1)
    tr.SetEnd(p2)
    tr.SetWidth(STUB_W)
    tr.SetLayer(layer)
    tr.SetNetCode(netcode)
    board.Add(tr)


def add_via(p, netcode):
    v = pcbnew.PCB_VIA(board)
    v.SetWidth(VIA_SIZE)
    v.SetDrill(VIA_DRILL)
    v.SetPosition(p)
    v.SetNetCode(netcode)
    board.Add(v)


fixed = 0
left = 0
for item in json.load(open(drc_path))["unconnected_items"]:
    ia, ib = item["items"]
    A = anchor(ia["description"], ia.get("pos") or ib.get("pos"))
    B = anchor(ib["description"], ib.get("pos") or ia.get("pos"))
    pair = f"{ia['description']} | {ib['description']}"
    if A is None or B is None or not A["found"] or not B["found"]:
        left += 1
        print("LEFT (unresolved)", pair)
        continue
    if A["net"] != B["net"]:
        left += 1
        print("LEFT (net mismatch)", pair)
        continue
    net = A["net"]
    nobj = board.FindNet("/" + net)
    if nobj is None:
        left += 1
        print("LEFT (no net)", net)
        continue
    netcode = nobj.GetNetCode()
    exempt_ids = {id(e) for e in A["exempt"] + B["exempt"] if e is not None}
    pA, pB = A["pos"], B["pos"]

    # common layer where both anchors' copper exists
    common = []
    if A["layers"] is None and B["layers"] is None:
        common = [pcbnew.F_Cu, pcbnew.B_Cu]
    elif A["layers"] is None:
        common = B["layers"]
    elif B["layers"] is None:
        common = A["layers"]
    else:
        common = [l for l in A["layers"] if l in B["layers"]]

    done = False
    # 1) straight route on a common layer
    for lay in common:
        if pA == pB:
            done = True  # already coincident (e.g. via on pad) — nothing to add
            break
        if seg_ok(pA, pB, lay, netcode, exempt_ids):
            if not DRY:
                add_track(pA, pB, lay, netcode)
            fixed += 1
            print("FIXED straight", net, A["kind"], B["kind"], "on", LAYER_NAME[lay])
            done = True
            break
    # 2) L route via opposite layer (only when both anchors have a single layer)
    if not done and A["layers"] and B["layers"]:
        oth = OTHER[A["layers"][0]]
        if oth in (B["layers"] or [oth]) or B["layers"] is None:
            pass
        elbow_layer = OTHER[A["layers"][0]]
        for elbow in (pcbnew.VECTOR2I(pA.x, pB.y), pcbnew.VECTOR2I(pB.x, pA.y)):
            if elbow in (pA, pB):
                continue
            if not via_ok(elbow, netcode, exempt_ids):
                continue
            if not seg_ok(pA, elbow, A["layers"][0], netcode, exempt_ids):
                continue
            blay = B["layers"][0] if B["layers"] else elbow_layer
            if not seg_ok(elbow, pB, blay, netcode, exempt_ids):
                continue
            if not DRY:
                add_track(pA, elbow, A["layers"][0], netcode)
                add_track(elbow, pB, blay, netcode)
                add_via(elbow, netcode)
            fixed += 1
            print("FIXED L", net, A["kind"], B["kind"], "elbow", round(elbow.x / NM, 2), round(elbow.y / NM, 2))
            done = True
            break
    # 3) cross-layer: straight on A's layer + joining via at B (or mirror)
    if not done and A["layers"] and B["layers"] and not common:
        for src, dst in ((A, B), (B, A)):
            if not seg_ok(src["pos"], dst["pos"], src["layers"][0], netcode, exempt_ids):
                continue
            if not via_ok(dst["pos"], netcode, exempt_ids):
                continue
            if not DRY:
                add_track(src["pos"], dst["pos"], src["layers"][0], netcode)
                add_via(dst["pos"], netcode)
            fixed += 1
            print("FIXED xlayer", net, src["kind"], "->", dst["kind"], "via at", round(dst["pos"].x / NM, 2), round(dst["pos"].y / NM, 2))
            done = True
            break
    if not done:
        left += 1
        print("LEFT", net, pair)

print("fixed", fixed, "left", left)
if fixed and not DRY:
    board.Save(board_path)
    print("saved")
