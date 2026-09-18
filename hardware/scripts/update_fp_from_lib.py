#!/usr/bin/env python3
"""Refresh every footprint on the board from the container KiCad library.

Usage: update_fp_from_lib.py <board.kicad_pcb>

Clears DRC lib_footprint_mismatch by replacing each embedded footprint
with the current library copy (reference, position, orientation, layer,
and per-pad net assignments are preserved).  Prints the per-reference
net-transfer log.
"""
import os
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
LIB = "/usr/share/kicad/footprints"

count, errors = 0, []
for fp in list(board.GetFootprints()):
    lib = fp.GetFPIDAsString().split(":")[0]
    name = fp.GetFPIDAsString().split(":")[-1]
    libdir = os.path.join(LIB, f"{lib}.pretty")
    if lib == "PinPath":
        libdir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])),
                              "pinpath.pretty")
    try:
        new = pcbnew.FootprintLoad(libdir, name)
    except Exception as e:
        errors.append((fp.GetReference(), f"load: {e}"))
        continue
    if new is None:
        errors.append((fp.GetReference(), "load returned None"))
        continue
    new.SetReference(fp.GetReference())
    new.SetPosition(fp.GetPosition())
    new.SetOrientationDegrees(fp.GetOrientationDegrees())
    new.SetLayer(fp.GetLayer())
    for pad in new.Pads():
        old = fp.FindPadByNumber(pad.GetPadName())
        if old is None:
            continue
        net = board.FindNet(old.GetNetname())
        if net is not None:
            pad.SetNet(net)
    try:
        board.Remove(fp)
        board.Add(new)
        count += 1
    except Exception as e:
        errors.append((fp.GetReference(), f"replace: {e}"))

print(f"replaced {count} footprints, errors: {len(errors)}")
for r, e in errors[:20]:
    print("  ERR", r, e)
if not errors:
    board.Save(sys.argv[1])
    print("saved", sys.argv[1])
else:
    sys.exit(1)
