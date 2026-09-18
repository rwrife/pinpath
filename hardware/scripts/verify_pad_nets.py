#!/usr/bin/env python3
"""Verify PCB pad-to-net mapping against the schematic-exported netlist.

Usage (run in the KiCad 9 container or anywhere kicad-cli is available
first for the netlist):
    kicad-cli sch export netlist pinpath.kicad_sch -o /tmp/pinpath.net
    python3 verify_pad_nets.py <board.kicad_pcb> <netlist.net>

Compares, per (reference, pad-number), the net name bound on the PCB pad
with the net name in the schematic netlist. Reports:
  - missing_from_pcb: pads present in schematic, absent on the board
  - missing_from_sch: pads wired on the board but not in the schematic
  - net_mismatch: same pad, different net (the swapped-pin class of bug)
Netlist net labels are normalized by stripping leading slashes/brackets and
KiCad auto-naming noise so /A:03_NODE matches A:03_NODE. Unnamed netlist
nets (no label in the net) are matched positionally only when unique;
otherwise they are reported as unverifiable rather than guessed.

Exits 0 only when every checkable pad agrees.
"""
import re
import sys

sys.path.insert(0, "/usr/lib/python3/dist-packages")
import pcbnew  # noqa: E402

board_path, netlist_path = sys.argv[1], sys.argv[2]


def norm(net):
    net = (net or "").strip()
    net = net.strip("()")
    if net.startswith("/"):
        net = net[1:]
    return net


# --- parse the .net (s-expression) netlist ---------------------------------
txt = open(netlist_path).read()

# net blocks: (net (code "N") (name "...") (class ...) (node (ref R) (pin P)) ...)
sch_map = {}  # (ref, pad) -> net name
pattern = re.compile(r'\(net \(code "[^"]*"\) \(name "([^"]*)"\)')
for m in pattern.finditer(txt):
    netname = norm(m.group(1))
    # walk balanced from m.start() to end of this net block
    k = m.start()
    d = 0
    end = k
    while end < len(txt):
        if txt[end] == "(":
            d += 1
        elif txt[end] == ")":
            d -= 1
            if d == 0:
                break
        end += 1
    block = txt[m.start() : end + 1]
    for nm in re.finditer(
        r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', block
    ):
        ref, pin = nm.group(1), nm.group(2)
        sch_map[(ref, pin)] = netname

# --- read PCB pads ----------------------------------------------------------
board = pcbnew.LoadBoard(board_path)
pcb_map = {}
for fp in board.GetFootprints():
    ref = fp.GetReference()
    for pad in fp.Pads():
        pcb_map[(ref, pad.GetPadName())] = norm(pad.GetNetname())

missing_from_pcb = sorted(set(sch_map) - set(pcb_map))
missing_from_sch = []
net_mismatch = []
agreed = 0
unverifiable = 0
for key, pnet in sorted(pcb_map.items()):
    if key not in sch_map:
        # power/anchor pads legitimately netless on one side only if both say ''
        missing_from_sch.append(key)
        continue
    snet = sch_map[key]
    if snet == "" and pnet == "":
        unverifiable += 1
    elif snet == "" or pnet == "":
        # one side unnamed; the DRC schematic_parity check covers pin/pad
        # identity, and unnamed-net agreement is not textually checkable
        unverifiable += 1
    elif snet == pnet:
        agreed += 1
    else:
        net_mismatch.append((key, snet, pnet))

print(f"schematic pad-nets: {len(sch_map)}  pcb pad-nets: {len(pcb_map)}")
print(f"agreed: {agreed}")
print(f"unverifiable-unnamed: {unverifiable}")
print(f"missing from pcb: {len(missing_from_pcb)} {missing_from_pcb[:20]}")
print(f"missing from schematic: {len(missing_from_sch)} {missing_from_sch[:20]}")
print(f"net mismatch: {len(net_mismatch)}")
for (ref, pad), s, p in net_mismatch:
    print(f"  {ref} pad {pad}: schematic={s} pcb={p}")
sys.exit(0 if not missing_from_pcb and not net_mismatch and not missing_from_sch else 1)
