# PinPath

> USB-powered RP2040 cable and wiring-harness tester for makers to map low-voltage pin continuity, catch opens, shorts, and crossovers, and save local test reports without cloud accounts.

## Overview

PinPath is planned as safe, repairable, open hardware for checking **disconnected, de-energized** passive cables and small wiring harnesses at a desk or workbench. Two configurable 16-position test banks connect through replaceable adapter boards or labeled flying leads. Firmware scans the conductors, reports the observed end-to-end map, and compares it with a user-selected expected map. A local desktop companion creates cable profiles and exports results.

This repository is currently a **requirements and backlog scaffold only**. The MVP requirements, architecture, protocol semantics, risk analysis, and verification matrix are frozen in editable documentation, but it does not yet contain a working schematic, PCB, firmware, app, validated BOM, ERC/DRC report, fabricated unit, or bench-test evidence.

## Motivation

Continuity mode on a multimeter works for one conductor at a time, but repetitive multi-pin checks are slow and easy to record incorrectly. Commercial harness testers can be excessive for hobby and repair work. PinPath aims to make common passive-cable checks repeatable while keeping the limits obvious: it is not a live-circuit probe, cable certifier, insulation tester, or safety instrument.

## Target users

- Makers assembling Dupont, JST-style, ribbon, and custom low-voltage harnesses
- Repair hobbyists checking intermittent or miswired passive cables
- Small workshops repeating the same fixture check in low volume
- Electronics learners who want a visible pin-to-pin map

## Concrete use cases

1. Connect both ends of an unpowered 10-conductor ribbon harness through adapters, select its saved profile, and identify one crossed pair.
2. Wiggle a repaired USB-data-only breakout harness during a timed scan and flag intermittent continuity for investigation; do **not** connect a live USB source.
3. Map an undocumented passive cable, label its observed connections, and export JSON/CSV for a project record.
4. Run a fixture self-test using a known loopback adapter before testing a batch.

## Intended workflow

1. Disconnect the cable or harness from every power source and device.
2. Inspect it and connect each end to the appropriate passive adapter or labeled flying leads.
3. Choose **map unknown cable** or an expected cable profile in the desktop app.
4. Start a bounded scan from the app or device button.
5. Review opens, shorts, crossovers, and intermittent observations; save or export the report.
6. Disconnect the item under test before changing adapters.

## MVP features

- Up to 16 conductors per side through two protected test banks
- Deterministic continuity map with open, short, and crossover classification
- Fixture self-test and explicit connected-voltage precheck design requirement
- Physical start/cancel button and non-color-only status indication
- USB CDC protocol; useful offline without Wi-Fi or an account
- Local profile/history storage with versioned JSON backup and CSV report export
- Replaceable adapter interface, starting with pin headers and labeled flying leads

## Non-goals

- Testing energized cables, mains wiring, PoE, batteries or battery packs, powered USB through a test bank, vehicles, medical or life-safety wiring, or unknown live circuits
- USB/Ethernet signal-integrity, bandwidth, impedance, insulation, hipot, precision-resistance, cable certification, or other certification measurements
- Four-wire milliohm measurement or calibrated resistance metrology
- Automatic connector identification
- Cloud dashboards, remote unattended operation, or production-line certification claims

## Safety and electrical limits

PinPath is planned for USB SELV power and de-energized passive assemblies only. The design must detect unexpected external voltage before enabling continuity scans, limit fault current, tolerate routine static handling, and fail visibly. These protections reduce risk but do not make live testing acceptable. Never connect mains, PoE, battery packs, powered USB hosts, vehicles, medical equipment, or safety-critical wiring. Final voltage/current limits will be set only after component datasheet review and measured bring-up.

## Privacy, permissions, and data storage

The desktop app will work locally with no account, telemetry, advertising, or cloud dependency. It requests USB-device access only when the user connects to PinPath and filesystem access only for explicit import/export. Profiles and reports live in an app-local SQLite database. Versioned JSON backup/restore and CSV report export keep the data user-owned. Export can omit free-text project notes.

## Accessibility expectations

All status must be conveyed with text/icon shape in addition to color. The app must support keyboard-only operation, screen readers, scalable text, strong focus indicators, reduced motion, and high-contrast themes. Connector positions and adapter documentation must use durable numbers, not color alone.

## Planned repository layout

```text
hardware/pinpath.kicad_pro    # planned editable KiCad project; not created yet
hardware/pinpath.kicad_sch    # planned editable schematic; not created yet
hardware/pinpath.kicad_pcb    # planned editable carrier PCB; not created yet
hardware/adapters/            # planned editable adapter-board sources
firmware/                     # planned RP2040 firmware
app/                          # planned local desktop companion
bom/preliminary-bom.csv       # planning-only candidates
bom/bom.csv                   # future schematic-derived tracked BOM
```

Final BOM data belongs in **KiCad schematic symbol properties** (including Manufacturer and MPN) and will be exported to tracked `bom/bom.csv`. The preliminary CSV is not an orderable BOM.

## Current status and milestones

- **Now:** frozen MVP requirements/architecture and planning-only candidate BOM
- **M1:** requirements, risk analysis, and adapter/test architecture
- **M2:** datasheet-backed component selection, editable KiCad schematic, and clean/documented ERC
- **M3:** PCB, DRC, firmware, protocol, and simulated fixture tests
- **M4:** desktop app, integration bring-up, assembly documentation, and measured limits
- **M5:** inspected fabrication outputs and reproducible release archive

## Development quickstart

No application or hardware source exists yet. The current repeatable documentation check is:

```bash
python3 tools/verify_requirements.py
```

After implementation skeletons land, expected commands are:

```bash
# Firmware (planned)
cmake -S firmware -B firmware/build
cmake --build firmware/build
ctest --test-dir firmware/build

# Desktop app (planned; Rust + Tauri + TypeScript)
cd app
npm ci
npm test
npm run tauri build
```

Those firmware/app commands are architectural targets, not current passing results. See [PLAN.md](PLAN.md), [system requirements](hardware/requirements.md), [architecture](docs/architecture.md), [risk analysis](docs/risk-analysis.md), [verification matrix](docs/verification-matrix.md), and the issue backlog for the implementation sequence.

## Licensing

Software and documentation scaffolding are MIT licensed. Before fabrication release, the project will add an explicit open-hardware license for KiCad and mechanical design sources and document third-party module/adapter licenses.
