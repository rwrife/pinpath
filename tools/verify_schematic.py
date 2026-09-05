#!/usr/bin/env python3
"""Verify PinPath's schematic/BOM deliverables without claiming physical evidence."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
ERRORS: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def read(path: Path) -> str:
    check(path.is_file(), f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


required_files = [
    HW / "pinpath.kicad_pro",
    HW / "pinpath.kicad_sch",
    HW / "pinpath.kicad_sym",
    HW / "sym-lib-table",
    HW / "fp-lib-table",
    HW / "pinpath.pretty" / "RaspberryPi_Pico_SMD_HandSolder.kicad_mod",
    HW / "reports" / "pinpath-erc.rpt",
    HW / "reports" / "pinpath-schematic.pdf",
    HW / "schematic-pinout-evidence.md",
    ROOT / "bom" / "bom.csv",
    ROOT / "bom" / "non-schematic-items.csv",
    HW / "adapters" / "known-loopback" / "known-loopback.kicad_pro",
    HW / "adapters" / "known-loopback" / "known-loopback.kicad_sch",
    HW / "adapters" / "known-loopback" / "known-loopback-erc.rpt",
    HW / "adapters" / "known-loopback" / "known-loopback-schematic.pdf",
    HW / "adapters" / "known-loopback" / "adapter-manifest.json",
]
for path in required_files:
    check(path.is_file(), f"missing file: {path.relative_to(ROOT)}")

# Project and safety state must remain machine-readable and fail closed.
for project in [HW / "pinpath.kicad_pro", HW / "adapters" / "known-loopback" / "known-loopback.kicad_pro"]:
    if project.is_file():
        json.loads(project.read_text())
limits = json.loads((HW / "selection" / "limits-rev-a.json").read_text())
check(limits.get("validated") is False, "limits must remain validated=false")
check(limits.get("firmware_scan_authorized") is False, "limits must keep firmware_scan_authorized=false")

sch = read(HW / "pinpath.kicad_sch")
refs = set(re.findall(r'\(property "Reference" "((?:U|D|R|C|J|SW|TP)\d+)"', sch))
expected_refs = (
    {f"U{i}" for i in range(1, 11)}
    | {f"D{i}" for i in range(1, 43)}
    | {f"R{i}" for i in range(1, 79)}
    | {f"C{i}" for i in range(1, 11)}
    | {f"J{i}" for i in range(1, 4)}
    | {"SW1"}
    | {f"TP{i}" for i in range(1, 13)}
)
check(refs == expected_refs, f"schematic reference set mismatch: missing={sorted(expected_refs-refs)} extra={sorted(refs-expected_refs)}")
check(len(refs) == 156, f"expected 156 BOM references, found {len(refs)}")
for field in ["Manufacturer", "MPN", "Supplier", "Source URL", "Estimated Unit Cost USD", "BOM Comments", "Evidence Status"]:
    check(sch.count(f'(property "{field}"') == 156, f"expected {field} on all 156 BOM symbols")
check(sch.count('(property "Estimated Unit Cost USD" "UNKNOWN"') == 156, "all volatile unit-cost fields must explicitly remain UNKNOWN")

# Every endpoint has the complete six-way protected internal-node fanout and
# exactly one connector-to-series-resistor external net.
for bank in "AB":
    for number in range(1, 17):
        endpoint = f"{bank}:{number:02d}"
        node = f"{endpoint}_NODE"
        check(sch.count(f'(label "{endpoint}"') == 2, f"{endpoint} must connect connector and one series resistor")
        expected_node_connections = 7 if number == 1 else 6  # TP10/TP11 add representative probes.
        check(sch.count(f'(label "{node}"') == expected_node_connections, f"{node} must have {expected_node_connections} protected-node connections")

# Manufacturer pin-table signatures and Pico footprint pad names.
for signature in [
    '(pin input line (at -11.43 -8.89 0) (length 2.54) (name "A0") (number "1"))',
    '(name "EN") (number "2")', '(name "VSS") (number "3")', '(name "S8") (number "9")',
    '(name "VDD") (number "13")', '(name "A1") (number "16")',
    '(name "IN") (number "1")', '(name "OUT") (number "2")',
    '(name "A1/GND") (number "1")', '(name "K2/+3V3") (number "2")', '(name "K1/A2/NODE") (number "3")',
    '(name "D1+") (number "1")', '(name "GND") (number "2")', '(name "D2-") (number "4")', '(name "NC") (number "5")',
    '(name "SWCLK") (number "D1")', '(name "SWD_GND") (number "D2")', '(name "SWDIO") (number "D3")',
]:
    check(signature in sch, f"missing pin-table signature: {signature}")

footprint = read(HW / "pinpath.pretty" / "RaspberryPi_Pico_SMD_HandSolder.kicad_mod")
for pad in [*(str(i) for i in range(1, 41)), "D1", "D2", "D3"]:
    check(f'(pad "{pad}"' in footprint, f"Pico footprint missing pad {pad}")
check('(generator_version "9.0")' in footprint, "Pico footprint must remain KiCad 9 compatible")

# Native ERC reports are committed evidence and must be warning/error free.
for report in [HW / "reports" / "pinpath-erc.rpt", HW / "adapters" / "known-loopback" / "known-loopback-erc.rpt"]:
    text = read(report)
    check("ERC messages: 0  Errors 0  Warnings 0" in text, f"non-clean ERC report: {report.relative_to(ROOT)}")

# PDFs are review supplements, not replacements for editable source.
for pdf in [HW / "reports" / "pinpath-schematic.pdf", HW / "adapters" / "known-loopback" / "known-loopback-schematic.pdf"]:
    check(pdf.is_file() and pdf.read_bytes().startswith(b"%PDF"), f"invalid PDF: {pdf.relative_to(ROOT)}")

# Native schematic-derived BOM coverage.
with (ROOT / "bom" / "bom.csv").open(newline="", encoding="utf-8") as handle:
    bom_rows = list(csv.DictReader(handle))
required_columns = [
    "References", "Quantity", "Value or Description", "Footprint or Package", "Manufacturer", "MPN", "Supplier",
    "Source URL", "Estimated Unit Cost USD", "Datasheet", "Notes", "Evidence Status",
]
check(list(bom_rows[0]) == required_columns, "unexpected bom/bom.csv columns")
check(sum(int(row["Quantity"]) for row in bom_rows) == 156, "BOM quantity total must equal 156")
for row in bom_rows:
    check(all(row[column].strip() for column in required_columns), f"blank required BOM field in {row.get('References')}")
    check(row["Estimated Unit Cost USD"] == "UNKNOWN", f"invented/stale cost value in {row['References']}")

with (ROOT / "bom" / "non-schematic-items.csv").open(newline="", encoding="utf-8") as handle:
    extra_rows = list(csv.DictReader(handle))
check(len(extra_rows) == 6, "expected six explicitly tracked non-schematic item rows")
check(all(row["Estimated Unit Cost USD"] == "UNKNOWN" for row in extra_rows), "non-schematic costs must remain UNKNOWN")

manifest = json.loads((HW / "adapters" / "known-loopback" / "adapter-manifest.json").read_text())
groups = manifest.get("expected_loopback_groups", [])
check(len(groups) == 16, "known-loopback manifest must have 16 groups")
check(groups == [[f"A:{i:02d}", f"B:{i:02d}"] for i in range(1, 17)], "known-loopback groups must be canonical one-to-one")
check(manifest.get("status") == "static_electrical_definition_not_physically_validated", "adapter status must not claim physical validation")

if ERRORS:
    for error in ERRORS:
        print(f"FAIL: {error}")
    print(f"SCHEMATIC_VERIFICATION: FAIL ({len(ERRORS)} findings)")
    sys.exit(1)

print(f"schematic_references={len(refs)}")
print(f"protected_endpoints={2*16}")
print(f"bom_rows={len(bom_rows)} bom_quantity={sum(int(row['Quantity']) for row in bom_rows)}")
print(f"adapter_loopback_groups={len(groups)}")
print("native_erc_reports=2 clean")
print("pdf_review_exports=2 valid")
print("physical_evidence=none")
print("SCHEMATIC_VERIFICATION: PASS")
