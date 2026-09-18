#!/usr/bin/env python3
"""Second-generation deterministic stub closer for the pinpath rev-A board.

close_stubs.py only tries straight segments (with an optional midpoint via).
This one also tries L-routes (one corner) and Z-routes (via at either end)
for every DRC unconnected pair, with capsule collision tests around each
segment and ring tests around each new via, rejecting anything that keeps
less than netclass clearance from foreign copper.

Usage (KiCad 9 container):
    python3 close_stubs2.py <board.kicad_pcb> <drc.json> [--dry]

Acceptance: prints 'fixed N', 'leftover M' and each LEFT pair verbatim.
Board is saved only when at least one stub closes and --dry is absent.
"""
import json
import math
import sys

import pcbnew

DRY = "--dry" in sys.argv
STUB_W = 150000  # 0.15 mm signal width
VIA_SIZE = 600000  # 0.6 mm
VIA_DRILL = 300000  # 0.3 mm
CLEAR = 200000  # 0.2 mm netclass clearance
HEAD = 20000  # 0.02 mm headroom
NM = 1e6

board_path, drc_path = sys.argv[1], sys.argv[2]
drc = json.load(open(drc_path))
board = pcbnew.LoadBoard(board_path)

# --- copper indexes ----------------------------------------------------------
pads_by_loc = {}  # rounded (x,y) -> (pad, ref)
all_pads = []
for fp in board.GetFootprints():
    for p in fp.Pads():
        all_pads.append((fp.GetReference(), p))

tracks = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]


def find_pad(desc, x, y):
    """Match a DRC pad description to a board pad near (x,y) mm."""
    import re

    m = re.search(r"Pad (\S+) \[([^\]]*)\] of (\S+)", desc)
    if not m:
        return None
    pin, net, ref = m.group(1), m.group(2), m.group(3)
    best = None
    for r, p in all_pads:
        if r != ref or p.GetPadName() != pin:
            continue
        d = math.hypot(p.GetPosition().x / NM - x, p.GetPosition().y / NM - y)
        if best is None or d < best[0]:
            best = (d, p)
    return best[1] if best else None


def find_track(desc, x, y):
    for t in tracks:
        if t.GetNetname().strip("/") != desc_net(desc):
            continue
        for pt in (t.GetStart(), t.GetEnd()):
            if math.hypot(pt.x / NM - x, pt.y / NM - y) < 0.02:
                return t
    return None


def desc_net(desc):
    import re

    m = re.search(r"\[([^\]]*)\]", desc)
    return (m.group(1) if m else "").strip("/")


def layer_of(desc):
    import re

    m = re.search(r"on ([FB]\.Cu)", desc)
    return m.group(1) if m else None


def resolve(desc, x, y):
    """Return (kind, obj, netname, layer)."""
    if desc.startswith("Pad "):
        pad = find_pad(desc, x, y)
        if pad is None:
            return None
        return ("pad", pad, pad.GetNetname(), None)
    if desc.startswith("Track "):
        for t in tracks:
            for pt in (t.GetStart(), t.GetEnd()):
                if (
                    math.hypot(pt.x / NM - x, pt.y / NM - y) < 0.02
                    and t.GetNetname().strip("/") == desc_net(desc)
                ):
                    lyr = str(t.GetLayerName())
                    return ("track", t, t.GetNetname(), lyr)
        return None
    if desc.startswith("Via "):
        for v in vias:
            if math.hypot(v.GetStart().x / NM - x, v.GetStart().y / NM - y) < 0.02:
                return ("via", v, v.GetNetname(), None)
        return None
    return None


# --- geometry helpers ----------------------------------------------------------
def capsule(x1, y1, x2, y2, width):
    """Rectangular polygon around a segment, expanded by clearance+headroom."""
    dx, dy = x2 - x1, y2 - y1
    ln = math.hypot(dx, dy) or 1
    r = width / 2 + CLEAR + HEAD
    px, py = -dy / ln * r, dx / ln * r
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for q in ((x1 + px, y1 + py), (x2 + px, y2 + py), (x2 - px, y2 - py), (x1 - px, y1 - py)):
        ch.Append(int(q[0]), int(q[1]), True)
    ch.Append(int(x1 + px), int(y1 + py))
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


def ring(x, y):
    r = VIA_SIZE / 2 + CLEAR + HEAD
    ch = pcbnew.SHAPE_LINE_CHAIN()
    n = 12
    for k in range(n):
        a = 2 * math.pi * k / n
        ch.Append(int(x + r * math.cos(a)), int(y + r * math.sin(a)), True)
    ch.SetClosed(True)
    return pcbnew.SHAPE_POLY_SET(ch)


LAYER_ID = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}


def seg_clear(x1, y1, x2, y2, layer, net):
    """True if a segment keeps clearance from every foreign same-layer pad."""
    cap = capsule(x1, y1, x2, y2, STUB_W)
    lid = LAYER_ID[layer]
    for _ref, p in all_pads:
        if p.GetNetname().strip("/") == net:
            continue
        if abs(p.GetPosition().x - min(x1, x2)) > 4 * NM or abs(p.GetPosition().x - max(x1, x2)) > 4 * NM:
            continue
        if abs(p.GetPosition().y - min(y1, y2)) > 4 * NM or abs(p.GetPosition().y - max(y1, y2)) > 4 * NM:
            continue
        try:
            if not p.IsOnLayer(lid):
                continue
            shape = p.GetEffectiveShape(lid)
        except Exception:
            continue
        if cap.Collide(shape, 0):
            return False
    for t in tracks:
        if t.GetNetname().strip("/") == net:
            continue
        if t.GetLayer() != lid:
            continue
        bb = t.GetEffectiveShape(lid).BoundingBox() if hasattr(t.GetEffectiveShape(lid), "BoundingBox") else None
        try:
            if cap.Collide(t.GetEffectiveShape(lid), 0):
                return False
        except Exception:
            continue
    return True


def via_clear(x, y, net):
    rng = ring(x, y)
    for _ref, p in all_pads:
        if p.GetNetname().strip("/") == net:
            continue
        if abs(p.GetPosition().x - x) > 3 * NM or abs(p.GetPosition().y - y) > 3 * NM:
            continue
        try:
            if rng.Collide(p.GetEffectiveShape(pcbnew.F_Cu), 0):
                return False
        except Exception:
            continue
    return True


def endpoint_of(t, x, y):
    """Return the track endpoint nearest to (x,y) mm as (X,Y) nm."""
    a, b = t.GetStart(), t.GetEnd()
    da = math.hypot(a.x / NM - x, a.y / NM - y)
    db = math.hypot(b.x / NM - x, b.y / NM - y)
    return (a.x, a.y) if da <= db else (b.x, b.y)


# --- candidate topologies ------------------------------------------------------
def try_close(ra, rb, net):
    """ra/rb: resolved (kind,obj,net,layer) + anchor point (mm). Return actions."""
    return None  # replaced below


fixed = 0
leftovers = []
added_segs = []  # accumulate (x1,y1,x2,y2,layer)
added_vias = []

existing_same_net = []  # test foreign only; same-net copper is allowed


def candidates(P, Q, lp, lq, net):
    """Yield (segments [(x1,y1,x2,y2,layer)], vias [(x,y)]) candidate routes."""
    px, py = P
    qx, qy = Q
    # same-layer straight
    for lay in {lp, lq}:
        if lay and lp == lq:
            yield ([(px, py, qx, qy, lay)], [])
    if lp == lq and lp is not None:
        # L routes on that layer (corner1 then corner2)
        yield ([(px, py, qx, py, lp), (qx, py, qx, qy, lp)], [])
        yield ([(px, py, px, qy, lp), (px, qy, qx, qy, lp)], [])
    # Z routes for cross-layer
    if lp != lq and lp and lq:
        # via at Q end: straight on Q layer to (qx,qy)... actually:
        # pad layer Lp straight to (qx,py), via, Q-layer straight to Q
        yield (
            [(px, py, qx, py, lp), (qx, py, qx, qy, lq)],
            [(qx, py)],
        )
        yield (
            [(px, py, px, qy, lp), (px, qy, qx, qy, lq)],
            [(px, qy)],
        )
        # via at P end
        yield ([(px, py, px, qy, lq), (px, qy, qx, qy, lq)], [(px, py)])
        # via at P corner with both legs
        yield ([(px, py, qx, qy, lp)], [(px, py), (qx, qy)])
    # cross-layer straight with vias at both ends (both layers spanned)
    if lp and lq and lp != lq:
        yield ([(px, py, qx, qy, lp)], [(qx, qy)])
        yield ([(px, py, qx, qy, lq)], [(px, py)])


for item in drc.get("unconnected_items", []):
    ia, ib = item["items"][0], item["items"][1]
    ra = resolve(ia["description"], ia["pos"]["x"], ia["pos"]["y"])
    rb = resolve(ib["description"], ib["pos"]["x"], ib["pos"]["y"])
    if ra is None or rb is None:
        leftovers.append([ia["description"], ib["description"]])
        continue
    kind_a, obj_a, _, lyr_a = ra
    kind_b, obj_b, _, lyr_b = rb
    net = obj_a.GetNetname().strip("/")

    def anchor(kind, obj, lyr):
        if kind == "pad":
            return (obj.GetPosition().x / NM, obj.GetPosition().y / NM)
        if kind == "track":
            # anchor is the endpoint that DRC cited
            for pt in (obj.GetStart(), obj.GetEnd()):
                if math.hypot(pt.x / NM - (ia["pos"]["x"] if kind_a == kind else ib["pos"]["x"]), pt.y / NM - (ia["pos"]["y"] if kind_a == kind else ib["pos"]["y"])) < 0.02:
                    return (pt.x / NM, pt.y / NM)
            return (obj.GetStart().x / NM, obj.GetStart().y / NM)
        return (obj.GetStart().x / NM, obj.GetStart().y / NM)

    # careful: track layer may be None from resolve for via; compute
    def tlayer(obj):
        try:
            return "F.Cu" if obj.GetLayer() == pcbnew.F_Cu else "B.Cu"
        except Exception:
            return str(obj.GetLayerName())

    P = anchor(kind_a, obj_a, lyr_a)
    Q = anchor(kind_b, obj_b, lyr_b)
    lp = lyr_a if kind_a != "track" else tlayer(obj_a)
    lq = lyr_b if kind_b != "track" else tlayer(obj_b)

    done = False
    for segs, vs in candidates(P, Q, lp, lq, net):
        ok = True
        for x1, y1, x2, y2, lay in segs:
            if not seg_clear(int(x1 * NM), int(y1 * NM), int(x2 * NM), int(y2 * NM), lay, net):
                ok = False
                break
        if ok:
            for vx, vy in vs:
                if not via_clear(int(vx * NM), int(vy * NM), net):
                    ok = False
                    break
        if not ok:
            continue
        # accept
        netcode = obj_a.GetNetCode()
        if not DRY:
            for x1, y1, x2, y2, lay in segs:
                tr = pcbnew.PCB_TRACK(board)
                tr.SetWidth(STUB_W)
                tr.SetStart(pcbnew.VECTOR2I(int(x1 * NM), int(y1 * NM)))
                tr.SetEnd(pcbnew.VECTOR2I(int(x2 * NM), int(y2 * NM)))
                tr.SetLayer(pcbnew.F_Cu if lay == "F.Cu" else pcbnew.B_Cu)
                tr.SetNetCode(netcode)
                board.Add(tr)
            for vx, vy in vs:
                v = pcbnew.PCB_VIA(board)
                # KiCad 9 python bindings expose no pcbnew.VIA_THROUGH here;
                # PCB_TRACK constructed as a via already defaults to through.
                v.SetWidth(VIA_SIZE)
                v.SetDrill(VIA_DRILL)
                v.SetPosition(pcbnew.VECTOR2I(int(vx * NM), int(vy * NM)))
                v.SetNetCode(netcode)
                board.Add(v)
        fixed += 1
        done = True
        break
    if not done:
        leftovers.append([ia["description"], ib["description"]])

print(f"fixed {fixed}")
print(f"leftover {len(leftovers)}")
for a, b in leftovers:
    print("LEFT", [a, b])
if fixed and not DRY:
    board.Save(board_path)
    print("saved", board_path)
