#!/usr/bin/env python3
"""Close DRC-reported unconnected stubs on the pinpath rev-A board (#4).

Run inside KiCad 9 pcbnew (parts-tally-kicad:9-arm64):
    python3 close_stubs.py <board.kicad_pcb> <drc.json> [--dry]

The DRC JSON `unconnected_items` pairs (pad, pad) or (pad/track, track).
For each pair we try, in order:
  A. straight segment on the layer of the track member (track->pad-center)
  B. straight segment on F.Cu then B.Cu (pad->pad), with a via at the
     midpoint for a diagonal Z route.
A candidate is accepted only if its buffered outline keeps full clearance
to every foreign pad/track on that layer (>= netclass clearance).
Everything else is left for a further router pass and printed verbatim.
"""
import json
import sys

import pcbnew

DRY = "--dry" in sys.argv
STUB_W = 150000  # 0.15 mm signal stub width, above fab minimum
board_path, drc_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)
NM = 1e6

# index pads and tracks by (x,y) anchor and description pieces
pads = []
for f in board.GetFootprints():
    for p in f.Pads():
        pads.append(p)
tracks = list(board.GetTracks())

drc = json.load(open(drc_path))
NM_RE = None

# Rebuild mapping from DRC coordinates by loading positions: the DRC JSON
# carries pos for each item. Match by net name + position proximity.
import re


def find_pad(netname, x, y):
    best, bd = None, 1e9
    for p in pads:
        if p.GetNetname().strip("/") != netname.strip("/"):
            continue
        c = p.GetPosition()
        d = (c.x / NM - x) ** 2 + (c.y / NM - y) ** 2
        if d < bd:
            bd, best = d, p
    return best if bd < 1.0 else None


def find_track(netname, x, y, layer):
    lay = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}[layer]
    best, bd = None, 1e9
    for t in tracks:
        if t.GetNetname().strip("/") != netname.strip("/") or t.GetLayer() != lay:
            continue
        for end in (t.GetStart(), t.GetEnd()):
            d = (end.x / NM - x) ** 2 + (end.y / NM - y) ** 2
            if d < bd:
                bd, best = d, (t, end)
    return best if bd < 1.0 else None


def parse_desc(s):
    # 'Pad 13 [/+3V3] of U6 on F.Cu', 'Track [/+3V3] on B.Cu, length 3.1020 mm',
    # 'Via [/A:05_NODE] on F.Cu - B.Cu', 'PTH pad 1 [/READY_LED] of TP8'
    m = re.match(r"^(?:PTH )?(Pad|pad) (\S+) \[/?([^\]]+)\] of (\S+)", s)
    if m:
        return ("pad", m.group(4), m.group(2), m.group(3), None)
    m = re.match(r"^Track \[/?([^\]]+)\] on ([FBB]\.?Cu)", s)
    if m:
        return ("track", None, None, m.group(1), m.group(2))
    m = re.match(r"^Via \[/?([^\]]+)\]", s)
    if m:
        return ("via", None, None, m.group(1), None)
    return None


import math


def seg_buffer(x1, y1, x2, y2, width):
    """Closed rectangular capsule polygon around a segment, inflated by
    width/2 + 0.1 mm headroom, as SHAPE_POLY_SET."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1.0
    r = int(width / 2 + 220000)  # 0.2 mm clearance + 0.02 headroom
    px, py = -dy / ln * r, dx / ln * r
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for (qx, qy) in ((x1 + px, y1 + py), (x2 + px, y2 + py),
                     (x2 - px, y2 - py), (x1 - px, y1 - py)):
        ch.Append(int(qx), int(qy), True)
    ch.Append(int(x1 + px), int(y1 + py))
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


def clear_ok(pts, netcode, width, layer, allow):
    """Edge-to-edge conservative: candidate segment is buffered by
    width/2 + 0.1 mm, so a zero remaining distance to any foreign copper
    outline means the real routed track would violate clearance."""
    for (x1, y1, x2, y2) in pts:
        ps = seg_buffer(x1, y1, x2, y2, width)
        for p in pads:
            if id(p) in allow or p.GetNetCode() == netcode or not p.IsOnLayer(layer):
                continue
            if ps.Collide(p.GetEffectiveShape(layer), 0):
                return False
        for t in tracks:
            if id(t) in allow or t.GetNetCode() == netcode or not t.IsOnLayer(layer):
                continue
            if ps.Collide(t.GetEffectiveShape(layer), 0):
                return False
    return True


def add_track(x1, y1, x2, y2, layer, netcode, width):
    seg = pcbnew.PCB_TRACK(board)
    seg.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    seg.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    seg.SetWidth(width)
    seg.SetLayer(layer)
    seg.SetNetCode(netcode)
    board.Add(seg)
    tracks.append(seg)


def add_via(pt, netcode):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(pt.x), int(pt.y)))
    via.SetWidth(600000)
    via.SetDrill(300000)
    via.SetNetCode(netcode)
    try:
        via.SetLayer(pcbnew.F_Cu, pcbnew.B_Cu)
    except Exception:
        pass
    board.Add(via)
    tracks.append(via)


fixed, leftover = 0, []
for u in drc.get("unconnected_items", []):
    ds = [parse_desc(i["description"]) for i in u["items"]]
    pos = [i["pos"] for i in u["items"]]
    if any(d is None for d in ds):
        leftover.append([i["description"] for i in u["items"]])
        continue
    kinds = {d[0] for d in ds}
    # Build endpoints in nm
    ends = []
    allow = set()
    ok = True
    netcode = None
    for d, p in zip(ds, pos):
        if d[0] == "pad":
            pad = find_pad(d[3], p["x"], p["y"])
            if pad is None:
                ok = False
                break
            ends.append(pad.GetPosition())
            allow.add(id(pad))
            netcode = pad.GetNetCode()
            netname = pad.GetNetname()
        elif d[0] == "track":
            hit = find_track(d[3], p["x"], p["y"], d[4])
            if hit is None:
                ok = False
                break
            t, endpt = hit
            ends.append(endpt)
            allow.add(id(t))
            netcode = t.GetNetCode()
            netname = t.GetNetname()
        else:  # via endpoint
            best, bd = None, 1e9
            for t in tracks:
                if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname().strip("/") == d[3].strip("/"):
                    c = t.GetPosition()
                    dd = (c.x / NM - p["x"]) ** 2 + (c.y / NM - p["y"]) ** 2
                    if dd < bd:
                        bd, best = dd, t
            if best is None:
                ok = False
                break
            ends.append(best.GetPosition())
            allow.add(id(best))
            netcode = best.GetNetCode()
            netname = best.GetNetname()
    if not ok or len(ends) != 2 or netcode is None:
        leftover.append([i["description"] for i in u["items"]])
        continue
    ax, ay = ends[0].x, ends[0].y
    bx, by = ends[1].x, ends[1].y
    width = STUB_W
    done = False
    # Straight routes on each copper layer
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        if clear_ok([(ax, ay, bx, by)], netcode, width, layer, allow):
            if not DRY:
                add_track(ax, ay, bx, by, layer, netcode, width)
            fixed += 1
            done = True
            break
    if not done:
        # Z route: corner + via for pad<->pad pairs on different stub dirs
        for (cx, cy) in ((ax, by), (bx, ay)):
            if (cx, cy) == (ax, ay) or (cx, cy) == (bx, by):
                continue
            seg1_f = clear_ok([(ax, ay, cx, cy)], netcode, width, pcbnew.F_Cu, allow)
            seg2_b = clear_ok([(cx, cy, bx, by)], netcode, width, pcbnew.B_Cu, allow)
            if seg1_f and seg2_b:
                if not DRY:
                    add_track(ax, ay, cx, cy, pcbnew.F_Cu, netcode, width)
                    add_via(pcbnew.VECTOR2I(int(cx), int(cy)), netcode)
                    add_track(cx, cy, bx, by, pcbnew.B_Cu, netcode, width)
                fixed += 1
                done = True
                break
    if not done:
        leftover.append([i["description"] for i in u["items"]])

if not DRY:
    board.Save(board_path)
print("fixed", fixed)
print("leftover", len(leftover))
for entry in leftover:
    print("LEFT", entry)
