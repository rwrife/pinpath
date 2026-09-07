#!/usr/bin/env python3
"""Run a bounded PinPath HIL exchange and record transcript JSON.

This script intentionally records `device_observation` unless a bench-record JSON
is provided with instrument/setup metadata.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any

import serial


def send_frame(port: serial.Serial, frame: dict[str, Any]) -> None:
    wire = json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
    if len(wire.encode("utf-8")) > 32768:
        raise ValueError("frame exceeds protocol max size")
    port.write((wire + "\n").encode("utf-8"))


def recv_frame(port: serial.Serial, timeout_s: float = 3.0) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        line = port.readline()
        if not line:
            continue
        return json.loads(line.decode("utf-8").strip())
    raise TimeoutError("timed out waiting for frame")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="USB CDC port (e.g. /dev/ttyACM0)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--repetitions", type=int, default=8)
    ap.add_argument("--output", required=True, help="Path to transcript JSON")
    ap.add_argument(
        "--bench-record",
        help="Optional path to controlled bench metadata JSON. Without this, evidence_context stays device_observation.",
    )
    args = ap.parse_args()

    transcript: list[dict[str, Any]] = []
    evidence_context = "device_observation"

    if args.bench_record:
        bench_data = json.loads(pathlib.Path(args.bench_record).read_text())
        required = {"instrument", "setup", "conditions", "hardware_revision"}
        if required.issubset(bench_data):
            evidence_context = "bench"
        else:
            raise ValueError("bench record missing required keys")

    with serial.Serial(args.port, args.baud, timeout=0.2) as port:
        frames = [
            {"v": 1, "type": "hello", "id": "hil-hello", "payload": {}},
            {"v": 1, "type": "precheck", "id": "hil-precheck", "payload": {"adapter_revision": "none"}},
            {
                "v": 1,
                "type": "scan",
                "id": "hil-scan",
                "payload": {"mode": "unknown_map", "repetitions": args.repetitions},
            },
        ]

        for frame in frames:
            send_frame(port, frame)
            transcript.append({"direction": "host_tx", "frame": frame})

            # Collect one or more responses for this request.
            while True:
                response = recv_frame(port)
                transcript.append({"direction": "device_rx", "frame": response})
                if response.get("id") == frame["id"] and response.get("type") in {
                    "hello_result",
                    "precheck_result",
                    "scan_result",
                    "self_test_result",
                    "cancelled",
                    "error",
                    "fault",
                }:
                    break

    out = {
        "schema": "pinpath-hil-transcript-v1",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_context": evidence_context,
        "notes": "Physical execution evidence only. Not equivalent to host simulation validation.",
        "transcript": transcript,
    }
    out_path = pathlib.Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
