# PinPath

> USB-powered RP2040 cable and wiring-harness tester for makers to map low-voltage pin continuity, catch opens, shorts, and crossovers, and save local test reports without cloud accounts.

## Overview

PinPath is planned as safe, repairable, open hardware for checking **disconnected, de-energized** passive cables and small wiring harnesses at a desk or workbench. Two configurable 16-position test banks connect through replaceable adapter boards or labeled flying leads. Firmware scans the conductors, reports the observed end-to-end map, and compares it with a user-selected expected map. A local desktop companion creates cable profiles and exports results.

This repository contains the frozen MVP requirements/architecture, a manufacturer-backed **rev-A candidate component selection**, the editable rev-A carrier schematic and routed carrier PCB candidate with source-of-truth BOM and clean native ERC/DRC evidence, RP2040 firmware with host-test scenario coverage, the Tauri 2 companion app with deterministic mock-protocol tests, and assembly/bring-up documentation. It still does not contain a fabricated unit or any bench-test evidence; `hardware/selection/limits-rev-a.json` deliberately keeps scanning unauthorized until physical characterization, and no release tag exists until that evidence does.

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
hardware/pinpath.kicad_pro    # editable rev-A carrier project
hardware/pinpath.kicad_sch    # editable carrier schematic and BOM source of truth
hardware/pinpath.kicad_pcb    # routed rev-A carrier candidate (see hardware/PCB-layout-evidence.md)
hardware/adapters/            # known-loopback electrical definition; PCB adapters planned
hardware/selection/           # rev-A candidate parts, evidence, calculations, and unvalidated limits
hardware/reports/             # ERC/DRC evidence and host-sim integration matrix
hardware/fab-out/             # gerber/drill/CPL candidates, fab inspection, board renders
firmware/                     # RP2040 safe-state firmware, host tests, scenario matrix, HIL fixture
app/                          # Tauri 2 desktop companion (Rust + TypeScript)
bom/bom.csv                   # schematic-derived tracked BOM
bom/non-schematic-items.csv   # cables, contacts, tools, and mechanical items
docs/                         # architecture, protocol, risk, verification matrix, assembly/bring-up docs
release/                      # release-readiness checklist and checksum generator
```

Final BOM data belongs in **KiCad schematic symbol properties** (including Manufacturer and MPN) and is exported to tracked `bom/bom.csv`. The preliminary CSV remains planning history; neither file is an order or a claim of current stock/price validation.

## Current status and milestones

- **Now:** frozen MVP requirements/architecture, rev-A candidate component selection, editable carrier schematic and routed carrier PCB candidate (0-error DRC, documented residuals), clean native ERC, schematic-derived BOM, RP2040 safe-state firmware with host tests and a 13-scenario integration matrix (host simulation), desktop companion with lint/tests/a11y/build/unsigned-package CI, assembly/bring-up/characterization documentation, and a release-readiness checklist (`release/RELEASE-READINESS.md`). Physical fabrication, assembly, and bench validation remain pending; scanning stays unauthorized until the limits record is validated on real hardware.
- **M1:** requirements, risk analysis, and adapter/test architecture
- **M2:** datasheet-backed component selection, editable KiCad schematic, and clean/documented ERC
- **M3:** PCB, DRC, firmware, protocol, and simulated fixture tests
- **M4:** desktop app, integration bring-up, assembly documentation, and measured limits
- **M5:** inspected fabrication outputs and reproducible release archive

## Development quickstart

The current repeatable static checks are:

```bash
python3 tools/verify_requirements.py
python3 hardware/selection/calculate_frontend.py --output hardware/selection/front-end-analysis.json
python3 -m unittest discover -s hardware/selection -p 'test_*.py' -v
python3 tools/verify_component_selection.py
python3 tools/verify_schematic.py
kicad-cli sch erc hardware/pinpath.kicad_sch --severity-all --exit-code-violations -o hardware/reports/pinpath-erc.rpt
```

After implementation skeletons land, expected commands are:

```bash
# Firmware (planned)
cmake -S firmware -B firmware/build
cmake --build firmware/build
ctest --test-dir firmware/build

# Desktop app (current baseline)
cd app
npm ci
npm run lint
npm run test:ci
npm run a11y
npm run build
npm run tauri:build
```

The firmware commands remain architectural targets. The app commands are now wired in CI and pass locally on this branch. See [PLAN.md](PLAN.md), [system requirements](hardware/requirements.md), [architecture](docs/architecture.md), [risk analysis](docs/risk-analysis.md), [verification matrix](docs/verification-matrix.md), [app/README.md](app/README.md), and [docs/usb-permissions.md](docs/usb-permissions.md) for status and limitations.

## Licensing

Software and documentation are MIT licensed (`LICENSE`); editable KiCad
hardware sources are distributed under the same MIT grant for the rev-A
candidate. Third-party code and documentation references are attributed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Manufacturer datasheets cited
in `hardware/selection/evidence-sources.json` remain the property of their
respective manufacturers.
