#!/usr/bin/env python3
"""Validate the issue #2 component-selection handoff using only stdlib."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "hardware" / "selection"


def fail(message: str) -> NoReturn:
    raise AssertionError(message)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_calculator():
    path = SELECTION / "calculate_frontend.py"
    spec = importlib.util.spec_from_file_location("pinpath_frontend", path)
    if spec is None or spec.loader is None:
        fail(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_analysis() -> None:
    expected = load_calculator().build_analysis()
    actual = load_json(SELECTION / "front-end-analysis.json")
    if actual != expected:
        fail("front-end-analysis.json is stale; regenerate with calculate_frontend.py")
    derived = actual["derived"]
    if derived["open_node_leakage_error_budget_v"] >= 0.02:
        fail("open-node leakage budget lost required margin")
    if derived["worst_32_node_high_delta_v"] <= 0.65:
        fail("32-node high-stimulus response lost required margin")
    if derived["worst_32_node_low_delta_v"] >= -0.40:
        fail("32-node low-stimulus response lost required margin")
    if derived["max_repetition_conversion_budget_s"] >= 20:
        fail("ADC conversion budget leaves insufficient 30-second overhead")


def verify_limits() -> None:
    limits = load_json(SELECTION / "limits-rev-a.json")
    if limits.get("validated") is not False:
        fail("candidate limits must remain validated=false before issue #7")
    if limits.get("firmware_scan_authorized") is not False:
        fail("candidate limits must not authorize firmware scanning")
    analysis = load_json(SELECTION / "front-end-analysis.json")["derived"]
    continuity = limits["continuity"]
    electrical = limits["electrical"]
    comparisons = {
        "worst_32_node_high_delta_v_static": analysis["worst_32_node_high_delta_v"],
        "worst_32_node_low_delta_v_static": analysis["worst_32_node_low_delta_v"],
        "maximum_64_repetition_conversion_budget_s": analysis["max_repetition_conversion_budget_s"],
        "default_8_repetition_conversion_budget_s": analysis["default_8_repetition_conversion_budget_s"],
    }
    for key, value in comparisons.items():
        if continuity.get(key) != value:
            fail(f"limits continuity field {key} does not match generated analysis")
    if electrical["driven_endpoint_short_to_ground_current_a_max_calculated"] != analysis[
        "driven_endpoint_short_to_ground_current_a"
    ]:
        fail("ground-fault current does not match generated analysis")
    if electrical["series_resistor_worst_calculated_fault_power_w"] != max(
        analysis["positive_external_fault"]["series_resistor_power_w"],
        analysis["negative_external_fault"]["series_resistor_power_w"],
    ):
        fail("resistor fault power does not match generated analysis")


def verify_handoff() -> None:
    handoff = load_json(SELECTION / "parts-handoff.json")
    if handoff.get("status") != "selected_for_schematic_capture_not_bench_validated":
        fail("handoff status must preserve the evidence boundary")
    required = {
        "references",
        "value",
        "quantity",
        "manufacturer",
        "mpn",
        "package",
        "footprint_hint",
        "datasheet",
        "supplier",
        "supplier_url",
        "bom_comments",
    }
    components = handoff.get("components", [])
    if len(components) < 15:
        fail("handoff is missing selected component classes")
    for component in components:
        missing = sorted(required - component.keys())
        if missing:
            fail(f"{component.get('references', '?')} missing fields: {missing}")
        for field in ("manufacturer", "mpn", "package", "datasheet", "supplier_url", "bom_comments"):
            value = component[field]
            if not isinstance(value, str) or not value.strip() or value.strip().upper() == "TBD":
                fail(f"{component['references']} has unresolved {field}")
    gpio = handoff["gpio_candidate_map"]
    for required_pin in ("GP9", "GP10", "GP26_ADC0", "GP27_ADC1", "GP28_ADC2"):
        if required_pin not in gpio:
            fail(f"GPIO map missing {required_pin}")


def verify_sources() -> None:
    sources = load_json(SELECTION / "evidence-sources.json")
    source_parts = {part for source in sources.get("sources", []) for part in source.get("parts", [])}
    handoff_parts = {component["mpn"] for component in load_json(SELECTION / "parts-handoff.json")["components"]}
    missing = sorted(handoff_parts - source_parts)
    if missing:
        fail(f"selected parts missing evidence sources: {missing}")
    if sources.get("retrieved_utc") != "2026-09-01":
        fail("evidence retrieval date missing or changed")


def verify_preliminary_bom() -> None:
    path = ROOT / "bom" / "preliminary-bom.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        fail("preliminary BOM is empty")
    required_columns = {
        "Planning_Status",
        "Item",
        "Qty",
        "Manufacturer",
        "MPN",
        "Estimated_Unit_Cost_USD",
        "Source_URL",
        "Availability_Evidence_UTC",
        "Notes",
    }
    if not required_columns.issubset(rows[0]):
        fail("preliminary BOM is missing required columns")
    selected = [row for row in rows if row["Planning_Status"].startswith("SELECTED")]
    if len(selected) < 18:
        fail("preliminary BOM is missing selected or non-schematic rows")
    for row in selected:
        for field in ("Manufacturer", "MPN", "Source_URL", "Availability_Evidence_UTC", "Notes"):
            if not row[field].strip() or row[field].strip().upper() == "TBD":
                fail(f"selected BOM row {row['Item']} has unresolved {field}")
        if row["Estimated_Unit_Cost_USD"] != "UNKNOWN":
            fail(f"selected BOM row {row['Item']} contains unsupported unit cost")
    planning_items = {row["Item"] for row in rows if row["Planning_Status"] == "PLANNING_ONLY"}
    required_planning = {
        "Custom main carrier PCB",
        "Passive flying-lead adapter",
        "Known loopback self-test adapter",
        "USB data cable",
        "Enclosure and fasteners",
        "Debug adapter cable",
    }
    if not required_planning.issubset(planning_items):
        fail("non-schematic/planning BOM items were dropped")


def verify_availability_csv() -> None:
    path = SELECTION / "availability-2026-09-01.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 18:
        fail("availability evidence is incomplete")
    for row in rows:
        if row["Retrieved_UTC"] != "2026-09-01":
            fail(f"availability row {row['MPN']} lacks retrieval date")
        if not row["Required_Action"].strip():
            fail(f"availability row {row['MPN']} lacks recheck action")


def main() -> int:
    checks = [
        verify_analysis,
        verify_limits,
        verify_handoff,
        verify_sources,
        verify_preliminary_bom,
        verify_availability_csv,
    ]
    try:
        for check in checks:
            check()
            print(f"PASS {check.__name__}")
    except (AssertionError, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        return 1
    print(f"PASS component selection ({len(checks)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
