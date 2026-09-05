# PinPath implementation plan

## Scope

Build a bench-top, USB-powered tester for disconnected passive cables and harnesses with up to 16 conductors per side. The MVP maps continuity and compares observations with expected profiles. It prioritizes transparent limits, repeatable self-test, replaceable adapters, local data ownership, and evidence from real tools.

## Architecture

### Hardware

- RP2040-class controller module on a custom two-layer carrier, with exact module/MPN selected from manufacturer data
- Two 16-position passive test banks exposed through keyed board connectors
- GPIO isolation/current limiting and external-voltage precheck circuitry selected only after fault analysis
- Physical start/cancel control, buzzer optional and muted by default, and non-color-only status indicator
- USB 5 V SELV power and USB CDC data; no battery, radio, mains interface, or power output to the cable under test
- Known loopback/self-test adapter and replaceable connector-specific adapter boards

### Firmware

- State machine: idle → precheck → self-test/scan → classify → report/fault
- One-active-drive scanning policy with all non-addressed nodes high impedance
- Debounced repeated observations for open/short/crossover/intermittent classification
- Versioned USB CDC protocol with bounded messages and explicit cancellation
- Hardware abstraction enabling host-side scan/classifier tests

### Companion app

- Tauri 2 desktop shell with Rust services and TypeScript UI for Windows 10/11, macOS, and Linux
- Local SQLite profiles/history; versioned JSON backup/restore and CSV export
- Serial-device discovery only after user action; no background network service
- Accessible profile editor, live matrix, result comparison, notes, and export

## Technology choices

- **RP2040 ecosystem:** Raspberry Pi Pico `SC0915` is the rev-A schematic candidate because it provides module USB/power/SWD and enough exposed GPIO/ADC for the muxed front end. This is manufacturer-datasheet-backed selection, not physical validation; see `hardware/selection/`.
- **KiCad:** editable, inspectable open-hardware source and schematic-property BOM workflow.
- **Pico SDK + CMake:** repeatable firmware build with host-test seams.
- **Tauri/Rust/TypeScript:** small local desktop package, robust serial/data boundary, and cross-platform UI without a cloud backend.
- **JSON Lines over USB CDC:** inspectable during bring-up and easy to implement on constrained firmware; the protocol includes explicit versioning and size limits.

## Milestones and dependency order

1. Freeze measurable requirements, misuse cases, fault model, connector numbering, and profile semantics.
2. Select controller/protection/interface parts from manufacturer datasheets; record Manufacturer/MPN in KiCad properties.
3. **Schematic-stage complete:** create the real KiCad project and schematic, export the BOM, run ERC, and review pin mapping. PCB/physical validation is not implied.
4. Lay out the carrier and first adapter, run DRC/analyzers, and inspect fabrication geometry.
5. Build firmware plus host simulation/classifier tests and reproducible flashing/recovery.
6. Build the desktop companion and local import/export/privacy controls.
7. Integrate on fabricated hardware; record precheck thresholds, scan behavior, expected measurements, and limitations.
8. Publish assembly instructions, troubleshooting, inspected manufacturing outputs, licenses, and a versioned release archive.

Milestone 1's normative baseline is captured in [system requirements](hardware/requirements.md), [architecture and profile semantics](docs/architecture.md), [protocol](docs/protocol.md), [misuse/fault analysis](docs/risk-analysis.md), and the [requirement-to-verification matrix](docs/verification-matrix.md). This closes the architecture definition only; the downstream evidence gates above remain open.

## Testing strategy

- Pure host tests for scan scheduling, matrix classification, protocol parsing, profile comparison, and report serialization
- Firmware build in CI plus static analysis where tool support permits
- App unit tests, accessibility checks, Rust/TypeScript linting, and platform builds
- KiCad ERC/DRC and project analyzers with every exception documented
- Loopback fixture tests and injected open/short/crossover matrices
- Bench measurements of GPIO fault current, unexpected-voltage precheck thresholds, supply current, and scan repeatability
- Clearly separate static analysis, host simulation, bench testing, and any later field use; no physical-test claim without recorded evidence

## Packaging and distribution

- Signed/notarized packages are a later milestone; initial app releases target unsigned development artifacts plus checksums
- UF2 firmware images accompanied by source revision and reproducible build instructions
- KiCad source, schematic PDF, Gerbers, drill files, CPL where applicable, BOM export, board renders, and release manifest in tagged hardware releases
- Assembly guide, adapter pinout sheets, and enclosure source files included when validated

## Risks and mitigations

- **Accidental energized connection:** prominent limits, external-voltage precheck, current limiting, fault state, and no scan enable after a failed precheck; these are mitigations, not permission for live testing.
- **GPIO damage through multi-node shorts:** fault-current analysis, protected front end, bounded drive time, and self-test before cable scan.
- **False intermittent results:** deterministic timing, repeated samples, fixture characterization, and quality flags rather than certainty claims.
- **Adapter misnumbering:** keyed connectors, pin-1 markings, canonical numbering, continuity-verified adapter definitions, and printable pinout sheets.
- **Cross-platform serial differences:** isolate adapters and test with recorded protocol fixtures before physical-device tests.
- **Supply-chain drift:** maintain Manufacturer/MPN in schematic properties, validate lifecycle/package, and record alternates only after review.

## Explicit non-goals

No energized/live wiring, mains, PoE, automotive, battery-pack, medical, life-safety, or production certification work. No impedance/bandwidth/hipot/insulation-resistance claims, no precision resistance measurement, no wireless/cloud service, and no universal connector library in the MVP.
