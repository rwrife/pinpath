#!/usr/bin/env python3
"""Issue #4 relayout for pinpath.kicad_pcb (deterministic bank-lane layout v3).

Courtyard sizes measured from the KiCad 9 libraries (mm, WxH at rot 0):
  SOT-23 3.95x3.49 | R_0805 1.99x3.45 | C_0805 2.05x3.49 | SC-70-6 2.89x3.29
  TSSOP-16 7.79x5.59 | Molex 29.25x13.76 | TP 3.19x3.19 | Pico 23.17x53.94
  SW tactile 9.59x4.29 | PinHeader 2x05 8.67x7.45 | MountingHole 6.99x7.00

Board 96 x 76 mm (REQ-MEC-001 ceiling 100x80). Run inside
parts-tally-kicad:9-arm64 (pcbnew 9.0.9).
"""
import sys

import pcbnew

BOARD = sys.argv[1]
W, H = 96.0, 76.0
MM = 1e6


def step(msg):
    print(f"step: {msg}", flush=True)


ESD = {f"D{i}" for i in range(33, 41)}
LED = {"D41", "D42"}
ANCHORS = {"U1", "J1", "J2", "J3", "H1", "H2", "H3", "H4"}

board = pcbnew.LoadBoard(BOARD)
foot = {f.GetReference(): f for f in board.GetFootprints()}
if len(foot) != 160:
    print(f"FATAL: expected 160 footprints, got {len(foot)}", file=sys.stderr)
    sys.exit(2)

netpins = {}
for f in board.GetFootprints():
    for p in f.Pads():
        n = p.GetNetname()
        if n:
            netpins.setdefault(n, []).append(f"{f.GetReference()}.{p.GetPadName()}")
step("nets")


def wanted_ident(ref):
    if ref == "U1":
        return "PinPath:RaspberryPi_Pico_SMD_HandSolder"
    if ref == "J3":
        return "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD"
    if ref == "SW1":
        return "Button_Switch_SMD:SW_Tactile_SPST_NO_Straight_CK_PTS636Sx25SMTRLFS"
    if ref == "U10" or (ref.startswith("D") and int(ref[1:]) <= 32):
        return "Package_TO_SOT_SMD:SOT-23"
    if ref in ESD:
        return "Package_TO_SOT_SMD:SOT-363_SC-70-6"
    if ref in LED:
        return "LED_SMD:LED_0805_2012Metric"
    if ref.startswith("TP"):
        return "TestPoint:TestPoint_Keystone_5015_Micro-Minature"
    if ref.startswith("H"):
        return "MountingHole:MountingHole_3.2mm_M3"
    if ref.startswith("J"):
        return "Connector_Molex:Molex_Micro-Fit_3.0_43045-1600_2x08_P3.00mm_Horizontal"
    if ref.startswith("R"):
        return "Resistor_SMD:R_0805_2012Metric"
    if ref.startswith("C"):
        return "Capacitor_SMD:C_0805_2012Metric"
    if ref.startswith("U"):
        return "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"
    raise SystemExit(f"no ident rule for {ref}")


for ref, f in foot.items():
    want = wanted_ident(ref)
    if f.GetFPIDAsString() != want:
        f.SetFPID(pcbnew.LIB_ID(*want.split(":")))
step("idents")

edges = [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]
if len(edges) != 4:
    raise SystemExit(f"expected 4 edge-cuts segments, found {len(edges)}")
for d, (x1, y1, x2, y2) in zip(edges, [(0, 0, W, 0), (W, 0, W, H),
                                       (W, H, 0, H), (0, H, 0, 0)]):
    d.SetStart(pcbnew.VECTOR2I(int(x1 * MM), int(y1 * MM)))
    d.SetEnd(pcbnew.VECTOR2I(int(x2 * MM), int(y2 * MM)))
step("outline")


def channel(bank, k):
    sig = netpins[f"{bank}:{k:02d}"]
    conn = [p for p in sig if p.split(".")[0] == ("J1" if bank == "A" else "J2")][0]
    series = [p.split(".")[0] for p in sig if p.split(".")[0].startswith("R")][0]
    node = netpins[f"{bank}:{k:02d}_NODE"]
    m = {"conn": conn, "series_r": series, "clamp": None, "precheck_r": []}
    for p in node:
        r = p.split(".")[0]
        if r in ESD or r in LED or r.startswith("TP"):
            continue
        elif r.startswith("D"):
            m["clamp"] = r
        elif r.startswith("R"):
            m["precheck_r"].append(r)
    return m


CH = {b: [channel(b, k) for k in range(1, 17)] for b in "AB"}

POS = {}


def place(ref, x, y, rot=0):
    POS[ref] = (x, y, rot)


# ------------------------------------------------------------ anchors
place("J1", 39.2, 9.5, 0)
place("J2", 68.6, 9.5, 0)
place("U1", 12.6, 44.0, 0)
place("H1", 5.0, 5.0)
place("H2", 91.0, 44.0)     # mid-right edge: top-right corner is taken by J2 body
place("H3", 91.0, 71.0)
place("H4", 28.5, 70.5)

# ------------------------------------------------------------ bank lanes
PITCH = 3.6
XA, XB = 26.5, 55.9
Y_SER1, Y_PRE1, Y_CLM1, Y_CLM2, Y_PRE2, Y_SER2 = 19.0, 23.0, 26.5, 31.0, 34.5, 38.0
Y_TVS, Y_MUX1, Y_MUX2 = 41.5, 47.0, 53.6
for bank, x0 in (("A", XA), ("B", XB)):
    for k in range(8):
        x = x0 + k * PITCH
        ch1, ch2 = CH[bank][k], CH[bank][8 + k]
        place(ch1["series_r"], x, Y_SER1, 0)
        place(ch2["series_r"], x, Y_SER2, 0)
        place(ch1["clamp"], x, Y_CLM1, 90)
        place(ch2["clamp"], x, Y_CLM2, 90)
        for pr in ch1["precheck_r"]:
            place(pr, x, Y_PRE1, 90)
        for pr in ch2["precheck_r"]:
            place(pr, x, Y_PRE2, 90)
    esd_row = sorted(ESD, key=lambda r: int(r[1:]))
    row = esd_row if bank == "A" else esd_row[4:]
    for i, ref in enumerate(row):
        place(ref, x0 + i * 3.15, Y_TVS, 0)
    mux = set()
    for k in range(1, 17):
        for p in netpins[f"{bank}:{k:02d}_NODE"]:
            r = p.split(".")[0]
            if r.startswith("U"):
                mux.add(r)
    refs = sorted(mux, key=lambda r: int(r[1:]))
    for i, ref in enumerate(refs[:4]):
        place(ref, x0 + 4.5 + (i % 2) * 9.0, Y_MUX1 + (i // 2) * 6.6, 0)

# ------------------------------------------------------------ decoupling band
cap3v3 = sorted([r for r in foot if r.startswith("C")], key=lambda r: int(r[1:]))
for i, ref in enumerate(cap3v3[:8]):
    place(ref, 29.0 + i * 3.7, 60.0, 90)
for ref in cap3v3[8:]:
    if ref == "C9":
        place(ref, 67.5, 60.0, 90)
    else:
        place(ref, 71.0, 60.0, 90)

# ------------------------------------------------------------ control resistor row
ctrl = sorted([r for r in foot if r.startswith("R") and int(r[1:]) >= 65],
              key=lambda r: int(r[1:]))
for i, ref in enumerate(ctrl):
    place(ref, 29.5 + i * 2.3, 63.5, 0)

# ------------------------------------------------------------ right TP column
tps = sorted([r for r in foot if r.startswith("TP")], key=lambda r: int(r[2:]))
for i, ref in enumerate(tps):
    place(ref, 84.0, 18.0 + i * 3.3, 90)

# ------------------------------------------------------------ bottom UI
place("U10", 63.0, 60.0, 0)
place("SW1", 47.0, 69.0, 0)
place("D41", 54.5, 68.5, 0)
place("D42", 58.0, 68.5, 0)
place("J3", 75.0, 68.0, 0)

missing = [r for r in foot if r not in POS]
step(f"plan built ({len(POS)} placed, missing {missing})")
if missing:
    sys.exit(3)

for ref, (x, y, rot) in POS.items():
    f = foot[ref]
    f.SetOrientationDegrees(rot)
    f.SetPosition(pcbnew.VECTOR2I(int(round(x * MM)), int(round(y * MM))))
step("positions applied")


def courtyard(f):
    ct = f.GetCourtyard(pcbnew.F_Cu).BBox()
    return [ct.GetX() / MM, ct.GetY() / MM, ct.GetRight() / MM, ct.GetBottom() / MM]


def box_at(f, x, y):
    # courtyard bbox translated so origin lands at (x, y)
    pos = f.GetPosition()
    c = courtyard(f)
    dx, dy = x - pos.x / MM, y - pos.y / MM
    return [c[0] + dx, c[1] + dy, c[2] + dx, c[3] + dy]


def hit(a, b, margin=0.2):
    return not (a[2] + margin <= b[0] or b[2] + margin <= a[0] or
                a[3] + margin <= b[1] or b[3] + margin <= a[1])


# ---- deterministic spiral legalization: anchors fixed, others find nearest
# collision-free spot near their planned position, largest first.
occupied = []
for ref in ANCHORS:
    occupied.append((ref, courtyard(foot[ref])))

movables = []
for ref, (x, y, rot) in POS.items():
    if ref in ANCHORS:
        continue
    f = foot[ref]
    c = courtyard(f)
    movables.append((-(c[2] - c[0]) * (c[3] - c[1]), ref, x, y))
movables.sort()

unplaced = []
for _, ref, x, y in movables:
    f = foot[ref]
    found = None
    step_mm = 0.5
    for ring in range(0, 121):                    # spiral rings up to 60 mm
        if ring == 0:
            cand = [(x, y)]
        else:
            r = ring * step_mm
            cand = []
            for i in range(-ring, ring + 1):
                cand += [(x + i * step_mm, y + r), (x + i * step_mm, y - r),
                         (x + r, y + i * step_mm), (x - r, y + i * step_mm)]
        for cx, cy in cand:
            box = box_at(f, cx, cy)
            if box[0] < 1.5 or box[1] < 1.5 or box[2] > W - 1.5 or box[3] > H - 1.5:
                continue
            if any(hit(box, ob) for _, ob in occupied):
                continue
            found = (cx, cy, box)
            break
        if found:
            break
    if found is None:
        unplaced.append(ref)
        continue
    cx, cy, box = found
    f.SetPosition(pcbnew.VECTOR2I(int(round(cx * MM)), int(round(cy * MM))))
    occupied.append((ref, box))
if unplaced:
    print("UNPLACED (no free spot):", unplaced)
step("legalized")


def areas():
    return {r: courtyard(foot[r]) for r in foot}


def overlaps(ca):
    refs = list(ca)
    out = []
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = ca[refs[i]], ca[refs[j]]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > 1e-6 and oy > 1e-6:
                out.append((refs[i], refs[j], ox, oy))
    return out


final = overlaps(areas())
print(f"remaining courtyard overlap pairs: {len(final)}")
for r1, r2, ox, oy in final[:30]:
    print("  STILL", r1, r2, round(ox, 2), round(oy, 2))
step("clamp")

for t in list(board.GetDrawings()):
    if t.GetLayer() in (pcbnew.F_SilkS, pcbnew.F_Fab) and getattr(t, "GetText", None):
        txt = t.GetText()
        if any(k in txt for k in ("rev", "PinPath", "BANK", "USB", "DE-ENERG",
                                  "START", "SWD", "RUN", "FAULT")):
            if not t.GetParent():
                board.Remove(t)


def silk(text, x, y, size=1.0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(int(x * MM), int(y * MM)))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetVisible(True)
    t.SetTextSize(pcbnew.VECTOR2I(int(size * MM), int(size * MM)))
    t.SetTextWidth(int(0.15 * MM))
    board.Add(t)


silk("BANK A", 27.0, 16.8, 0.8)
silk("BANK B", 56.5, 16.8, 0.8)
silk("PinPath rev-A", 33.0, 57.6, 0.8)
silk("DE-ENERGIZED CABLES ONLY", 45.0, 57.6, 0.8)
silk("SWD", 75.0, 74.3, 0.8)
step("silk")

board.Save(BOARD)
print("saved", BOARD)
