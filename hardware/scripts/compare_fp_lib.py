#!/usr/bin/env python3
"""Compare each embedded footprint copy against its library .kicad_mod.

For every footprint on the board whose library is a system library, find the
matching .kicad_mod file, extract the (pad ...) blocks from both texts, and
report whether the pad geometry sets are identical. Non-pad graphics/text
differences (which still trigger KiCad's lib_footprint_mismatch warning) are
counted separately. This tells us whether the 44 DRC warnings are cosmetic
(graphics-only drift) or material (pad-map drift).

Usage: python3 compare_fp_lib.py <board.kicad_pcb> [lib_root=/usr/share/kicad/footprints]
Pure text/stdlib — runs on the host, no pcbnew needed.
"""
import os
import re
import sys

board_path = sys.argv[1]
lib_root = sys.argv[2] if len(sys.argv) > 2 else "/usr/share/kicad/footprints"

txt = open(board_path).read()


def extract_blocks(text, keyword):
    """Return list of balanced (keyword ...) blocks."""
    blocks = []
    i = 0
    needle = f"({keyword}"
    while True:
        j = text.find(needle, i)
        if j < 0:
            break
        depth = 0
        k = j
        while k < len(text):
            if text[k] == "(":
                depth += 1
            elif text[k] == ")":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        blocks.append(text[j : k + 1])
        i = k + 1
    return blocks


def footprint_blocks(text):
    out = []
    for b in extract_blocks(text, "footprint"):
        m = re.search(r'\(property "Reference" "([A-Za-z0-9_]+)"', b)
        ref = m.group(1) if m else "?"
        out.append((ref, b))
    return out


def pad_sig(block):
    """Normalized pad identity set from a footprint block."""
    sig = set()
    for p in extract_blocks(block, "pad"):
        name = re.match(r'\(pad "?([^")\s]*)"?', p).group(1)
        tpr = re.search(r"\(type ([a-z_]+)", p)
        typ = tpr.group(1) if tpr else "?"
        shape = re.search(r"\sshape ([A-Z_]+)", p)
        size = re.search(r"\(size ([\d.]+) ([\d.]+)\)", p)
        pos = re.search(r"\(at ([\d.\-]+) ([\d.\-]+)(?: ([\d.\-]+))?\)", p)
        layers = re.search(r'\(layers([^)]*)\)', p)
        drill = re.search(r"\(drill(?: offset)?([^)]*)\)", p)
        sig.add(
            (
                name,
                typ,
                shape.group(1) if shape else "?",
                tuple(size.groups()) if size else ("?", "?"),
                tuple(v and round(float(v), 4) or 0 for v in pos.groups())
                if pos
                else None,
                tuple(sorted(re.findall(r'"([^"]+)"', layers.group(1))))
                if layers
                else (),
                drill.group(1).strip() if drill else "",
            )
        )
    return sig


def fp_name_of(block):
    m = re.match(r'\(footprint "([^"]+)"', block)
    return m.group(1) if m else "?"


def find_lib_file(fname):
    """Resolve 'LIB:name' or 'name' to a .kicad_mod path under lib_root."""
    lib, _, name = fname.rpartition(":")
    name = name.replace(" ", "")
    if lib:
        cand = os.path.join(lib_root, f"{lib}.pretty", f"{name}.kicad_mod")
        if os.path.isfile(cand):
            return cand
    for d in os.listdir(lib_root):
        cand = os.path.join(lib_root, d, f"{name}.kicad_mod")
        if os.path.isfile(cand):
            return cand
    return None


embedded = {}
for ref, b in footprint_blocks(txt):
    fname = fp_name_of(b)
    embedded[ref] = (fname, b)

diff_report = {}
for ref, (fname, block) in sorted(embedded.items()):
    # Try exact name first (KiCad .kicad_mod files may contain spaces),
    # then the space-stripped variant.
    lib, _, name = fname.rpartition(":")
    libpath = None
    if lib:
        cand = os.path.join(lib_root, f"{lib}.pretty", f"{name}.kicad_mod")
        if os.path.isfile(cand):
            libpath = cand
    if libpath is None:
        for d in os.listdir(lib_root):
            cand = os.path.join(lib_root, d, f"{name}.kicad_mod")
            if os.path.isfile(cand):
                libpath = cand
                break
    if libpath is None:
        cand = os.path.join(lib_root, "MountingHole.pretty", "MountingHole_3.2mm_M3.kicad_mod")
        if "MountingHole" in fname and os.path.isfile(cand):
            libpath = cand
    if libpath is None:
        diff_report[ref] = (fname, "LIB-NOT-FOUND", None)
        continue
    lib_txt = open(libpath).read()
    lib_sig = pad_sig(lib_txt)
    emb_sig = pad_sig(block)
    if lib_sig == emb_sig:
        diff_report[ref] = (fname, "PADS-IDENTICAL", None)
    else:
        only_emb = emb_sig - lib_sig
        only_lib = lib_sig - emb_sig
        diff_report[ref] = (fname, "PADS-DIFFER", (sorted(map(str, only_emb))[:4], sorted(map(str, only_lib))[:4]))

counts = {}
for ref, (fname, status, det) in diff_report.items():
    counts[status] = counts.get(status, 0) + 1
print("status counts:", counts)
for ref, (fname, status, det) in diff_report.items():
    if status != "PADS-IDENTICAL":
        print(f"  {ref} [{fname}] {status}")
        if det:
            print("     emb:", det[0])
            print("     lib:", det[1])
