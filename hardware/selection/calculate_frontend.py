#!/usr/bin/env python3
"""Dependency-free static DC analysis for the PinPath rev-A candidate front end.

This is a resistor-network calculation, not SPICE and not physical evidence.
It intentionally uses conservative selected-part limits where available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULTS = {
    "stimulus_min_v": 3.0,
    "stimulus_max_v": 3.63,
    "bias_high_nom_v": 1.8,
    "bias_feed_resistor_ohm": 1_000.0,
    "series_resistor_nom_ohm": 10_000.0,
    "series_resistor_tolerance": 0.01,
    "bias_resistor_nom_ohm": 100_000.0,
    "bias_resistor_tolerance": 0.01,
    "mux_ron_max_ohm": 9.75,
    "mux_off_leakage_max_a": 1.5e-9,
    "esd_leakage_max_a": 10e-9,
    "clamp_reverse_leakage_budget_a": 100e-9,
    "clamp_forward_drop_at_1ma_max_v": 0.410,
    "external_fault_abs_v": 5.0,
    "sample_budget_us": 120.0,
    "endpoints": 32,
    "sense_readings_per_drive_polarity": 32,
    "stimulus_polarities": 2,
    "max_repetitions": 64,
}


def _solve_linear_3(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    """Solve a non-singular 3x3 system with Gaussian elimination."""
    augmented = [row[:] + [value] for row, value in zip(matrix, rhs)]
    for column in range(3):
        pivot = max(range(column, 3), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-18:
            raise ValueError("singular front-end model")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        for index in range(column, 4):
            augmented[column][index] /= scale
        for row in range(3):
            if row == column:
                continue
            scale = augmented[row][column]
            for index in range(column, 4):
                augmented[row][index] -= scale * augmented[column][index]
    return [augmented[index][3] for index in range(3)]


def connected_group(
    size: int,
    stimulus_v: float,
    bias_v: float,
    series_ohm: float,
    bias_ohm: float,
    mux_ron_ohm: float,
) -> dict[str, float | int | None]:
    """Solve one driven endpoint connected to ``size - 1`` symmetric endpoints."""
    if not 1 <= size <= 32:
        raise ValueError("group size must be 1..32")
    if size == 1:
        drive = (stimulus_v / mux_ron_ohm + bias_v / bias_ohm) / (
            1.0 / mux_ron_ohm + 1.0 / bias_ohm
        )
        return {
            "group_size": size,
            "drive_node_v": drive,
            "remote_node_v": None,
            "remote_delta_from_bias_v": None,
            "drive_current_a": (stimulus_v - drive) / mux_ron_ohm,
        }

    remote_count = size - 1
    matrix = [
        [1 / mux_ron_ohm + 1 / bias_ohm + 1 / series_ohm, -1 / series_ohm, 0],
        [-1 / series_ohm, size / series_ohm, -remote_count / series_ohm],
        [0, -1 / series_ohm, 1 / bias_ohm + 1 / series_ohm],
    ]
    rhs = [stimulus_v / mux_ron_ohm + bias_v / bias_ohm, 0, bias_v / bias_ohm]
    drive, _cable, remote = _solve_linear_3(matrix, rhs)
    return {
        "group_size": size,
        "drive_node_v": drive,
        "remote_node_v": remote,
        "remote_delta_from_bias_v": remote - bias_v,
        "drive_current_a": (stimulus_v - drive) / mux_ron_ohm,
    }


def external_fault(
    external_v: float,
    rail_v: float,
    series_ohm: float,
    clamp_drop_v: float,
) -> dict[str, float]:
    """Conservative DC current after a single endpoint is driven externally."""
    if external_v >= 0:
        current = max(0.0, (external_v - rail_v - clamp_drop_v) / series_ohm)
    else:
        current = -max(0.0, (abs(external_v) - clamp_drop_v) / series_ohm)
    return {
        "external_v": external_v,
        "clamp_current_a": current,
        "series_resistor_power_w": current * current * series_ohm,
    }


def precheck_node(
    external_v: float,
    external_source_ohm: float,
    bias_v: float,
    series_ohm: float,
    bias_ohm: float,
) -> float:
    """Endpoint voltage for a Thevenin external source during precheck."""
    external_path = external_source_ohm + series_ohm
    return (external_v / external_path + bias_v / bias_ohm) / (
        1.0 / external_path + 1.0 / bias_ohm
    )


def _round_nested(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, list):
        return [_round_nested(item) for item in value]
    if isinstance(value, dict):
        return {key: _round_nested(item) for key, item in value.items()}
    return value


def build_analysis(group_sizes: Iterable[int] = (1, 2, 4, 8, 16, 32)) -> dict:
    p = DEFAULTS
    series_min = p["series_resistor_nom_ohm"] * (1 - p["series_resistor_tolerance"])
    series_max = p["series_resistor_nom_ohm"] * (1 + p["series_resistor_tolerance"])
    bias_min = p["bias_resistor_nom_ohm"] * (1 - p["bias_resistor_tolerance"])
    bias_max = p["bias_resistor_nom_ohm"] * (1 + p["bias_resistor_tolerance"])

    # Weakest connected response: low stimulus rail, maximum endpoint series R,
    # minimum bias R (strongest opposing bias), maximum mux RON.
    high_stimulus = [
        connected_group(size, p["stimulus_min_v"], 0.0, series_max, bias_min, p["mux_ron_max_ohm"])
        for size in group_sizes
    ]
    low_stimulus = [
        connected_group(size, 0.0, p["bias_high_nom_v"], series_max, bias_min, p["mux_ron_max_ohm"])
        for size in group_sizes
    ]

    open_error = bias_max * (
        p["mux_off_leakage_max_a"]
        + p["esd_leakage_max_a"]
        + p["clamp_reverse_leakage_budget_a"]
    )
    positive_fault = external_fault(
        p["external_fault_abs_v"],
        p["stimulus_max_v"],
        series_min,
        p["clamp_forward_drop_at_1ma_max_v"],
    )
    negative_fault = external_fault(
        -p["external_fault_abs_v"],
        p["stimulus_max_v"],
        series_min,
        p["clamp_forward_drop_at_1ma_max_v"],
    )
    contention_current = p["stimulus_max_v"] / (2 * series_min)
    grounded_endpoint_current = p["stimulus_max_v"] / series_min
    sample_count = (
        p["endpoints"]
        * p["sense_readings_per_drive_polarity"]
        * p["stimulus_polarities"]
        * p["max_repetitions"]
    )
    sample_time = sample_count * p["sample_budget_us"] / 1_000_000
    bias_pull_low_current = p["bias_high_nom_v"] / p["bias_feed_resistor_ohm"]
    precheck_cases = []
    for source_ohm in (0.0, 10_000.0):
        for external_v in (-5.0, -1.0, 0.0, 1.8, 3.3, 5.0):
            low = precheck_node(external_v, source_ohm, 0.0, series_max, bias_min)
            high = precheck_node(
                external_v,
                source_ohm,
                p["bias_high_nom_v"],
                series_max,
                bias_min,
            )
            low_pass = 0.0 <= low <= 0.20
            high_pass = abs(high - p["bias_high_nom_v"]) <= 0.20
            precheck_cases.append(
                {
                    "external_v": external_v,
                    "external_source_ohm": source_ohm,
                    "low_phase_node_v_unclamped": low,
                    "high_phase_node_v_unclamped": high,
                    "low_phase_pass": low_pass,
                    "high_phase_pass": high_pass,
                    "overall_pass": low_pass and high_pass,
                }
            )

    result = {
        "schema_version": "1.0.0",
        "evidence_context": "static_calculation",
        "physical_tested": False,
        "spice_simulated": False,
        "model": "symmetric linear DC nodal model; ideal cable connections; no contact resistance or capacitance",
        "inputs": p,
        "derived": {
            "series_resistor_min_ohm": series_min,
            "series_resistor_max_ohm": series_max,
            "bias_resistor_min_ohm": bias_min,
            "bias_resistor_max_ohm": bias_max,
            "open_node_leakage_error_budget_v": open_error,
            "high_stimulus_groups": high_stimulus,
            "low_stimulus_groups": low_stimulus,
            "worst_32_node_high_delta_v": high_stimulus[-1]["remote_delta_from_bias_v"],
            "worst_32_node_low_delta_v": low_stimulus[-1]["remote_delta_from_bias_v"],
            "two_drive_contention_current_a": contention_current,
            "driven_endpoint_short_to_ground_current_a": grounded_endpoint_current,
            "positive_external_fault": positive_fault,
            "negative_external_fault": negative_fault,
            "max_repetition_adc_conversion_count": sample_count,
            "max_repetition_conversion_budget_s": sample_time,
            "default_8_repetition_conversion_budget_s": sample_time * 8 / p["max_repetitions"],
            "bias_control_pull_low_current_a": bias_pull_low_current,
            "fixed_external_source_precheck_cases": precheck_cases,
        },
        "provisional_thresholds": {
            "precheck_low_phase_max_v": 0.20,
            "precheck_high_phase_max_abs_error_from_measured_reference_v": 0.20,
            "continuity_min_abs_delta_from_bias_v": 0.25,
            "note": "Provisional calculation thresholds only; limits-rev-a.json keeps validated=false until controlled bench characterization.",
        },
    }
    return _round_nested(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(build_analysis(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
