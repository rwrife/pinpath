#!/usr/bin/env python3
"""A* clearance-aware rerouter for nets that FreeRouter could not finish.

For every net cited by a DRC unconnected pair: delete that net's existing
tracks/vias, then route pad-to-pad hops on a 0.1 mm two-layer grid with A*,
treating all foreign copper (other nets' tracks, vias, and pads) inflated by
track half-width + clearance + margin as obstacles, with a via transition
cost. Same-net pads are allowed as start/goal cells even where buried.
After routing, GND pours are refilled (they carve clearance around new
copper), and the board is saved.

Usage (KiCad 9 container): astar_reroute.py <board.kicad_pcb> <drc.json> [--dry]
"""
import heapq
import json
import re
import sys

import pcbnew

DRY = "--dry" in sys.argv
PITCH = 100000  # 0.1 mm grid
W = 130000  # new track width 0.13 mm (scan_fanout net class)
VIA_SIZE = 450000
VIA_DRILL = 200000
CLEAR = 130000  # scan_fanout net class clearance
MARGIN = 10000
VIA_COST = 40
NM = 1e6

NET_FILTER = []
if "--net" in sys.argv:
    i = sys.argv.index("--net")
    NET_FILTER = sys.argv[i + 1].split(",")

board_path, drc_path = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)

LAYER_NAME = {pcbnew.F_Cu: "F.Cu", pcbnew.B_Cu: "B.Cu"}
LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
obstruct_pad = W / 2 + CLEAR + MARGIN  # pad inflation per side
obstruct_tr = W / 2 + CLEAR + MARGIN

pat_end = re.compile(r"Track \[/(.*?)\] on ([FB])\.Cu")
pat_via = re.compile(r"(?:Blind/Buried )?Via \[/(.*?)\] on")
pat_pad = re.compile(r"(?:SMD |PTH )?[Pp]ad (\S+) \[/(.*?)\] of (\S+)")

# 1. which nets are cited unconnected
nets_bad = set()
for item in json.load(open(drc_path))["unconnected_items"]:
    for it in item["items"]:
        m = pat_end.search(it["description"]) or pat_via.search(it["description"])
        if m:
            nets_bad.add(m.group(1))
            continue
        m = pat_pad.search(it["description"])
        if m:
            nets_bad.add(m.group(2))

# 2. collect board geometry
pads = []  # (ref, name, netname, pos, bbox, layers)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        bb = pad.GetBoundingBox()
        pads.append((fp.GetReference(), pad.GetPadName(), pad.GetNetname(), pad.GetPosition(), bb, pad.GetLayer()))

tracks = list(board.GetTracks())


def grid_rect(obstruct_rows, bb, infl):
    x0 = max(0, int((bb.GetX() - infl) // PITCH))
    y0 = max(0, int((bb.GetY() - infl) // PITCH))
    x1 = min(GW - 1, int((bb.GetRight() + infl) // PITCH))
    y1 = min(GH - 1, int((bb.GetBottom() + infl) // PITCH))
    for y in range(y0, y1 + 1):
        row = obstruct_rows[y]
        for x in range(x0, x1 + 1):
            row[x] = 1


GX0, GY0 = 0, 0
bb_outline = board.GetEdgeArea().GetBoundingBox() if hasattr(board, "GetEdgeArea") else None
xs = [t.GetPosition().x for fp in board.GetFootprints() for t in [fp]]
# board 96x76 mm (proven from Edge.Cuts probe)
GW = int(96 * NM // PITCH) + 2
GH = int(76 * NM // PITCH) + 2

# 3. process each bad net: wipe copper, rebuild obstacle map from remaining
#    copper, route pad chain with A*
fixed_nets = 0
failed = []
for net in sorted(nets_bad):
    if NET_FILTER and net not in NET_FILTER:
        continue
    gname = "/" + net
    nobj = board.FindNet(gname)
    if nobj is None:
        failed.append((net, "no net object"))
        continue
    netcode = nobj.GetNetCode()
    # pads on this net
    npads = [(r, n, p, lay) for (r, n, nn, p, bb, lay) in pads if nn == gname]
    if len(npads) < 2:
        failed.append((net, f"{len(npads)} pads"))
        continue
    # NOTE: old copper for this net is removed only AFTER a successful
    # A* plan, so a failed net is left exactly as it was. Obstacle maps
    # below ignore this net's own copper — same-net copper needs no
    # clearance, and it is about to be replaced.

    # obstacle bitmaps per layer (rebuild cheaply per net)
    obstruct = {L: [bytearray(GW) for _ in range(GH)] for L in LAYERS}
    for (r, n, nn, p, bb, lay) in pads:
        if nn == gname:
            continue
        # pads occupy their own layer(s); SMT pads single layer, THT both
        target_layers = [lay] if lay in LAYERS else LAYERS
        for L in target_layers:
            grid_rect(obstruct[L], bb, obstruct_pad)
    for t in tracks:
        if t.GetNetCode() == netcode or t.GetNetCode() == 0:
            continue
        bb = t.GetBoundingBox()
        if t.Type() == pcbnew.PCB_VIA_T:
            for L in LAYERS:
                grid_rect(obstruct[L], bb, obstruct_pad)
        else:
            grid_rect(obstruct[t.GetLayer()], bb, obstruct_tr)
    # keepout from board edge
    edge = 500000  # 0.5 mm copper edge clearance
    ex0 = int(edge // PITCH)
    for y in range(GH):
        for x in range(min(ex0, GW)):
            for L in LAYERS:
                obstruct[L][y][x] = 1
        for x in range(max(GW - ex0, 0), GW):
            for L in LAYERS:
                obstruct[L][y][x] = 1

    def cell(p):
        return (min(max(int(round((p.x) / PITCH)), 0), GW - 1),
                min(max(int(round((p.y) / PITCH)), 0), GH - 1))

    def astar(src, dst):
        """src/dst: ((x,y), layer_idx). Returns list of ((x,y,L_idx)) or None."""
        sx, sy = src[0]
        dx, dy = dst[0]
        # allow goal cell even if inside a same-net pad (pads excluded above,
        # but a same-net pad may sit inside another net's inflation — relax goal)
        start, goal = src, dst
        if obstruct[LAYERS[start[1]]][sy][sx]:
            # nudge start free within 2 cells
            for dr in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                nx, ny = sx + dr[0] * 2, sy + dr[1] * 2
                if 0 <= nx < GW and 0 <= ny < GH and not obstruct[LAYERS[start[1]]][ny][nx]:
                    start = ((nx, ny), start[1])
                    sx, sy = nx, ny
                    break
        if obstruct[LAYERS[goal[1]]][dy][dx]:
            found = False
            for rad in (1, 2, 3):
                for ddx in range(-rad, rad + 1):
                    for ddy in range(-rad, rad + 1):
                        nx, ny = dx + ddx, dy + ddy
                        if 0 <= nx < GW and 0 <= ny < GH and not obstruct[LAYERS[goal[1]]][ny][nx]:
                            goal, found = ((nx, ny), goal[1]), True
                            break
                    if found:
                        break
                if found:
                    break
            if not found:
                return None
        h = lambda c, l: abs(c[0] - dx) + abs(c[1] - dy)
        counter = iter(range(1 << 30))
        pq = [(h(start[0], start[1]), 0, next(counter), start, None)]
        best = {start: 0}
        prev = {}
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        expansions = 0
        while pq:
            f, g, _, cur, parent = heapq.heappop(pq)
            if cur == goal:
                path = [cur]
                node = cur
                while node in prev:
                    node = prev[node]
                    path.append(node)
                return path[::-1]
            if best.get(cur, 1 << 30) < g:
                continue
            prev.setdefault(cur, parent)
            expansions += 1
            if expansions > 400000:
                return None
            (cx, cy), li = cur
            for ddx, ddy in dirs:
                nx, ny = cx + ddx, cy + ddy
                if not (0 <= nx < GW and 0 <= ny < GH):
                    continue
                if obstruct[LAYERS[li]][ny][nx]:
                    continue
                ng = g + 1
                nc = ((nx, ny), li)
                if best.get(nc, 1 << 30) <= ng:
                    continue
                best[nc] = ng
                heapq.heappush(pq, (ng + h((nx, ny), li), ng, next(counter), nc, cur))
            # layer transition
            lj = 1 - li
            if not obstruct[LAYERS[lj]][cy][cx]:
                ng = g + VIA_COST
                nc = ((cx, cy), lj)
                if best.get(nc, 1 << 30) <= ng:
                    continue
                best[nc] = ng
                heapq.heappush(pq, (ng + h((cx, cy), lj), ng, next(counter), nc, cur))
        return None

    # route chain: pad0 -> pad1 -> ... (greedy nearest-neighbour order)
    order = [npads[0]]
    remaining = npads[1:]
    while remaining:
        last = order[-1]
        d, nxt = min(((abs(p2[2].x - last[2].x) + abs(p2[2].y - last[2].y), p2) for p2 in remaining))
        order.append(nxt)
        remaining.remove(nxt)

    ok_all = True
    segments = []  # (p1_nm, p2_nm, layer)
    vias = []
    for (ref1, n1, pos1, lay1), (ref2, n2, pos2, lay2) in zip(order, order[1:]):
        li = 0 if lay1 == pcbnew.F_Cu else 1
        lj = 0 if lay2 == pcbnew.F_Cu else 1
        path = astar((cell(pos1), li), (cell(pos2), lj))
        if path is None:
            ok_all = False
            failed.append((net, f"{ref1}.{n1}->{ref2}.{n2} no path"))
            break
        for a, b in zip(path, path[1:]):
            if a[1] == b[1]:
                segments.append((a[0], b[0], LAYERS[a[1]]))
            else:
                vias.append(a[0])
    if not ok_all:
        # do not wipe the old copper — keep this net exactly as it was
        continue
    # merge collinear segments
    merged = []
    for p1, p2, lay in segments:
        if merged and merged[-1][2] == lay and merged[-1][1] == p1:
            q = merged[-1]
            if (q[0][0] == p1[0] == p2[0]) or (q[0][1] == p1[1] == p2[1]):
                merged[-1] = (q[0], p2, lay)
                continue
        merged.append((p1, p2, lay))
    # success: wipe this net's old copper, then write the new plan
    for t in list(board.GetTracks()):
        if t.GetNetCode() == netcode:
            if not DRY:
                board.Remove(t)
    tracks = [t for t in tracks if t.GetNetCode() != netcode]
    if not DRY:
        for p1, p2, lay in merged:
            tr = pcbnew.PCB_TRACK(board)
            tr.SetStart(pcbnew.VECTOR2I(p1[0] * PITCH, p1[1] * PITCH))
            tr.SetEnd(pcbnew.VECTOR2I(p2[0] * PITCH, p2[1] * PITCH))
            tr.SetWidth(W)
            tr.SetLayer(lay)
            tr.SetNetCode(netcode)
            board.Add(tr)
        seen_v = set()
        for (gx, gy) in vias:
            if (gx, gy) in seen_v:
                continue
            seen_v.add((gx, gy))
            v = pcbnew.PCB_VIA(board)
            v.SetWidth(VIA_SIZE)
            v.SetDrill(VIA_DRILL)
            v.SetPosition(pcbnew.VECTOR2I(gx * PITCH, gy * PITCH))
            v.SetNetCode(netcode)
            board.Add(v)
    fixed_nets += 1
    print(f"ROUTED {net}: {len(merged)} segs, {len(set(map(tuple, vias)))} vias")

print("fixed nets:", fixed_nets, "failed:", failed)
if fixed_nets and not DRY:
    zones = list(board.Zones())
    pcbnew.ZONE_FILLER(board).Fill(zones)
    board.Save(board_path)
    print("saved")
