# PinPath system requirements baseline

Status: **frozen for MVP architecture**. These are design requirements, not measured results. Electrical values that depend on selected parts are carried in the versioned limits record defined by REQ-SAF-006 and remain unvalidated until issues #2 and #7 provide manufacturer and bench evidence.

The words **shall**, **shall not**, and **only** are normative. Every requirement has one stable identifier, rationale, and planned verification route. The complete requirement-to-evidence mapping is in [`../docs/verification-matrix.md`](../docs/verification-matrix.md).

## Scope and operating context

### REQ-SCP-001 — De-energized passive assemblies only

**Requirement.** PinPath shall scan only a cable, adapter, or wiring harness that the operator has disconnected from every power source and active device. The setup flow shall require an explicit acknowledgement of this condition before a precheck or scan.

**Rationale.** The front end is a low-energy continuity mapper, not a live-circuit probe.

**Planned verification.** Documentation inspection, app workflow test, protocol state test, and bench lockout test.

### REQ-SCP-002 — Prohibited applications remain explicit

**Requirement.** Product, app, firmware, assembly, and release documentation shall explicitly prohibit connection to mains, PoE, batteries or battery packs, powered USB, vehicles, medical or life-safety wiring, and energized circuits. PinPath shall not claim hipot, insulation, impedance, bandwidth, precision resistance, cable certification, or protective-instrument capability.

**Rationale.** Protection features reduce damage risk but cannot make prohibited use safe or establish certification-grade performance.

**Planned verification.** Documentation and release-package inspection.

### REQ-SCP-003 — Supervised local operation

**Requirement.** Operation shall be human-supervised at an indoor, dry bench. The device and core app workflow shall work without a network service, account, telemetry, or remote-unattended control.

**Rationale.** The intended use is local troubleshooting of passive assemblies with the operator present.

**Planned verification.** Architecture inspection, app integration test with networking disabled, and permissions audit.

## Functional behavior

### REQ-FUN-001 — Two fixed-size test banks

**Requirement.** The MVP shall expose exactly 16 canonical positions on Bank A and 16 on Bank B. Every position shall be addressable for precheck, stimulus, sensing, mapping, and reporting.

**Rationale.** A fixed 32-endpoint model bounds hardware, protocol, UI, and test complexity.

**Planned verification.** Schematic inspection, firmware endpoint-table test, app matrix test, and assembled-board continuity inspection.

### REQ-FUN-002 — Deliberate start

**Requirement.** A self-test or cable scan shall begin only after a compatible host command or a deliberate local start action, and only after all safety gates pass. Device connection alone shall never start a scan.

**Rationale.** Deliberate initiation gives the operator a final chance to verify the disconnected setup.

**Planned verification.** Firmware state-machine tests, app workflow tests, and bench observation.

### REQ-FUN-003 — Unknown-map semantics

**Requirement.** Unknown-map mode shall report the observed undirected connectivity groups among all 32 canonical endpoints without assigning intended pin roles. Isolated endpoints shall be reported as open/unconnected observations, not omitted.

**Rationale.** A complete normalized graph is deterministic and preserves evidence for undocumented passive cables.

**Planned verification.** Classifier unit tests covering isolated, paired, same-bank, and multi-node groups; app fixture tests; and loopback bench tests.

### REQ-FUN-004 — Expected-map comparison

**Requirement.** Expected-map mode shall compare normalized expected connectivity groups with normalized observed groups and report matched groups, opens, shorts, crossovers, and unstable observations according to [`../docs/architecture.md`](../docs/architecture.md). An incomplete or cancelled scan shall not produce a pass result.

**Rationale.** Explicit normalized semantics avoid ambiguous pair-ordering and classification precedence.

**Planned verification.** Classifier unit/property tests, protocol fixture tests, and known-fault loopback tests.

### REQ-FUN-005 — Bounded repeated scan

**Requirement.** A scan shall use 8 repetitions by default, accept only 3 through 64 repetitions, and terminate within 30 seconds after scan acceptance. Each endpoint shall receive the same scheduled stimulus/sample opportunities unless cancellation or fault makes the result partial.

**Rationale.** Repetition detects unstable contacts; explicit bounds prevent unbounded drive exposure or hostile protocol requests.

**Planned verification.** Scheduler unit/property tests, protocol boundary tests, timing simulation, and bench timing measurement.

### REQ-FUN-006 — Cancellation

**Requirement.** A local or host cancellation request shall stop further stimulus scheduling, enter the safe condition before emitting `cancelled`, and mark any accumulated observation as partial and non-passing.

**Rationale.** Cancellation is a safety transition, not only a UI action.

**Planned verification.** Firmware cancellation tests at every scan phase, protocol tests, and bench GPIO observation.

## Electrical safety and recovery

### REQ-SAF-001 — Defined safe condition

**Requirement.** The test-bank safe condition shall disable every active drive/enable path and place all MCU-connected scan pins in input/high-impedance mode with internal pulls disabled. Only documented passive bias, protection, and high-impedance precheck networks may remain connected. Status, USB, and debug circuits outside the bank boundary may remain active.

**Rationale.** A single unambiguous condition is needed for reset, fault, cancellation, and disconnect handling.

**Planned verification.** Schematic/static review, firmware register-state tests, reset/fault simulation, and bench impedance/GPIO observation.

### REQ-SAF-002 — Hardware and startup default safe

**Requirement.** Hardware shall default to REQ-SAF-001 while the MCU is unpowered, held in reset, booting, or its bank-control pins are high impedance. Firmware shall establish and verify the safe condition before accepting USB commands or local start input.

**Rationale.** Safety cannot depend on application firmware having already run.

**Planned verification.** Datasheet-backed schematic analysis, power/reset simulation where applicable, startup unit test, and powered/off/reset bench checks.

### REQ-SAF-003 — One active drive maximum

**Requirement.** During stimulus, no more than one canonical endpoint shall have an enabled active drive path. Before changing endpoints, firmware shall disable the current path, verify the drive-control shadow state is empty, then enable the next path. Every non-addressed endpoint shall remain in REQ-SAF-001 except for passive sense networks.

**Rationale.** Break-before-make scheduling bounds GPIO-to-GPIO and multi-node short stress.

**Planned verification.** Scheduler invariant/property test, static pin-mux audit, logic simulation, and multi-channel bench capture.

### REQ-SAF-004 — All-endpoint external-voltage precheck

**Requirement.** Precheck shall run with all stimulus paths disabled, evaluate every A:01–A:16 and B:01–B:16 endpoint, and pass only when each reading and the precheck reference/self-diagnostic are within the active limits record. Any missing, saturated, out-of-range, or internally inconsistent reading shall fail closed.

**Rationale.** Sampling only one bank or treating sensor faults as zero voltage could enable stimulus into an externally driven assembly.

**Planned verification.** Schematic analysis, tolerance simulation, firmware injected-ADC tests, and swept-voltage bench tests.

### REQ-SAF-005 — Single-use recent precheck token

**Requirement.** A passing precheck shall create a token bound to the hardware revision, limits revision, adapter manifest, and connection session. The token shall be consumed by one self-test or scan, shall expire after 5 seconds, and shall be invalidated by cancel, fault, reset, watchdog, USB disconnect, adapter change indication, or incompatible command.

**Rationale.** A stale result must not authorize later stimulus after relevant state changes.

**Planned verification.** State-machine and boundary-timing tests plus disconnect/reset bench tests.

### REQ-SAF-006 — Versioned validated electrical limits

**Requirement.** Each hardware revision shall provide a machine-readable limits record containing precheck pass/fail thresholds and tolerance, maximum allowed drive and injection current, stimulus voltage, per-endpoint drive duration, continuity decision thresholds, and applicable temperature/supply range. Selection calculations shall prove worst-case short and clamp currents do not exceed the lowest applicable continuous rating of the selected MCU/front-end/protection parts. Firmware shall refuse scanning when the limits record is absent, invalid, unvalidated, or incompatible.

**Rationale.** Part-dependent numbers must be traceable rather than guessed in the architecture document.

**Planned verification.** Manufacturer-datasheet review, checked calculations, SPICE where useful, schema/static validation, firmware compatibility tests, and bench characterization.

### REQ-SAF-007 — Fault and reset recovery

**Requirement.** Failed precheck, self-test fault, invalid protocol state, malformed or oversized input, host disconnect, watchdog event, brownout/reset, internal invariant failure, or unexpected voltage during a scan shall cause or preserve REQ-SAF-001. Recovery shall require clearing the fault where allowed and completing a new precheck; no command may override this gate.

**Rationale.** Every abnormal path must converge on the same safe state.

**Planned verification.** Fault-injection state tests, parser tests, reset simulation, and bench fault matrix.

### REQ-SAF-008 — Fixture self-test

**Requirement.** The system shall support a revisioned known-loopback adapter manifest. Self-test shall require a fresh precheck, compare every declared loopback group and every expected-isolated endpoint, reject an incompatible adapter/revision, and report a non-passing fault on any open, extra connection, short, or unstable observation.

**Rationale.** Fixture integrity must be checked independently of the cable profile.

**Planned verification.** Manifest/schema tests, simulated loopback faults, and physical known-adapter tests.

### REQ-SAF-009 — Host has no unsafe override

**Requirement.** USB commands shall not disable precheck, extend electrical limits, select raw GPIOs, force an active drive, or clear a non-recoverable hardware fault. Diagnostic commands shall be read-only with respect to test-bank stimulus unless they use the same gated scan scheduler.

**Rationale.** The app is untrusted input and must not bypass device-enforced safety.

**Planned verification.** Protocol API audit, negative parser/state tests, and USB fuzz tests.

## Interfaces and numbering

### REQ-IFC-001 — Canonical endpoint names

**Requirement.** All source, protocol, UI, reports, silkscreen, adapter manifests, and tests shall use `A:01` through `A:16` and `B:01` through `B:16`. Names are case-sensitive; zero padding is mandatory; raw GPIO numbers shall not cross the firmware hardware-abstraction boundary.

**Rationale.** Stable human-visible names prevent connector orientation and implementation-pin leakage.

**Planned verification.** Documentation inspection, schema tests, source lint, silkscreen inspection, and app accessibility test.

### REQ-IFC-002 — Adapter mapping and orientation

**Requirement.** Every adapter shall have a revisioned manifest mapping each canonical endpoint to a physical connector reference, manufacturer pin number, mating-face orientation, pin-1/key landmark, and user-visible label. Reversal shall be mechanically keyed where practical and detectably non-passing in self-test where not.

**Rationale.** Connector views and pin-number conventions differ; a manifest makes the transformation explicit.

**Planned verification.** Drawing/manifest inspection, KiCad connector cross-check, schema test, and adapter continuity test.

### REQ-IFC-003 — Bounded USB CDC framing

**Requirement.** Device/app transport shall be newline-delimited UTF-8 JSON with a maximum encoded frame length of 32,768 bytes, maximum nesting depth 8, maximum string length 256 Unicode scalar values, and no more than 496 undirected edge records or 32 endpoint/group records in applicable arrays. Input shall be rejected before unbounded allocation or state change.

**Rationale.** The bounds cover every possible undirected pair of 32 endpoints while limiting parser resource use.

**Planned verification.** Parser unit/property tests at and beyond each boundary, memory review, and app/firmware interoperability tests.

### REQ-IFC-004 — Version and revision compatibility

**Requirement.** Every command and response shall carry protocol major version, request identifier, and message type. `hello_result` shall identify firmware version, hardware revision, limits revision, capabilities, and current state. An unknown protocol major or incompatible hardware/limits/adapter revision shall be rejected without enabling stimulus; if received while `armed`, it shall invalidate the precheck token and leave `armed`.

**Rationale.** Explicit compatibility prevents old software from applying invalid electrical assumptions.

**Planned verification.** Schema inspection and cross-version protocol tests.

### REQ-IFC-005 — USB/debug boundary

**Requirement.** USB shall provide SELV power and CDC data only. Debug shall use a documented local SWD/vendor recovery interface and shall not expose a path from USB power or debug power to any test-bank endpoint. Firmware update shall require local physical access; no network or application-protocol updater is in MVP scope.

**Rationale.** Power, debug, and test-bank domains must remain explicit and bounded.

**Planned verification.** Schematic/net review, datasheet review, DRC/cross-analysis, and continuity bench test.

## Classification and reports

### REQ-REP-001 — Stable classification vocabulary and precedence

**Requirement.** The only conductor-result classes shall be `matched`, `open`, `short`, `crossover`, `unstable`, and `not_evaluated`. Classification shall follow the normalized definitions and precedence in [`../docs/architecture.md`](../docs/architecture.md): `unstable` is evaluated first; a complete bijective two-endpoint `crossover` is evaluated before `short`; merged or multi-node groups remain `short`; and any unstable observation prevents a pass.

**Rationale.** Stable terms let firmware, app, fixtures, and exported records agree.

**Planned verification.** Golden-vector classifier tests, app rendering tests, and documentation terminology audit.

### REQ-REP-002 — Evidence-bearing reports

**Requirement.** A saved/exported result shall include schema version, UTC timestamp, mode, canonical expected and observed groups, per-class details, repetition counts, completion state, quality flags, hardware/firmware/protocol/limits/adapter revisions, and exactly one evidence context from the closed enum `host_simulation`, `device_observation`, `bench`, or `field_observation`. `device_observation` means a real-device result without the controlled instrument/setup record required for `bench`; it is not validation evidence. The report shall not claim cable certification or electrical safety.

**Rationale.** Results need enough context to reproduce interpretation without overstating evidence.

**Planned verification.** Schema tests, serialization round-trip tests, export inspection, and terminology audit.

### REQ-REP-003 — Required quality flags

**Requirement.** Reports shall explicitly represent `precheck_passed`, `self_test_passed`, `complete`, `stable`, `limits_validated`, and `revision_compatible` as independent booleans, plus a non-empty reason code whenever any flag is false. A passing comparison requires all applicable flags true.

**Rationale.** Independent, non-color-only flags expose why a result is not trustworthy.

**Planned verification.** Classifier/report unit tests, app accessibility tests, and export inspection.

## Data ownership and accessibility

### REQ-DAT-001 — Local data ownership

**Requirement.** Profiles and reports shall be stored locally, shall be deletable by the user, and shall support versioned JSON backup/restore without a cloud account or required network connection.

**Rationale.** The user owns potentially sensitive harness/project data.

**Planned verification.** App storage/migration/backup tests and offline integration test.

### REQ-DAT-002 — Explicit bounded export

**Requirement.** JSON/CSV export shall occur only after explicit user action, validate destination and schema, escape spreadsheet-significant and control characters, and allow exclusion of free-text project notes and unique device identifiers.

**Rationale.** Export must not create command-injection or unintended-disclosure paths.

**Planned verification.** App security tests with hostile text fixtures and manual export inspection.

### REQ-ACC-001 — Non-color-only device and connector status

**Requirement.** Bank identity, positions, pin 1, device state, precheck result, scan progress, completion, and fault shall be distinguishable by durable text, number, icon shape, pattern, or timing code in addition to any color. Critical fault and ready indications shall not share the same non-color cue.

**Rationale.** Operation and wiring must not depend on color perception or fragile legends.

**Planned verification.** Schematic/PCB/enclosure review, accessibility inspection, and user-interface tests.

### REQ-ACC-002 — Accessible desktop interaction

**Requirement.** The app shall support keyboard-only operation, programmatic names/roles/states, ordered focus, status announcements, scalable text, high contrast, and reduced motion. Every 16×16 matrix result shall have an equivalent textual endpoint/class description.

**Rationale.** The workflow and results must remain usable with assistive technology.

**Planned verification.** Automated accessibility checks, keyboard/screen-reader test plan, and cross-platform manual review.

## Hardware, mechanical, environment, and sourcing

### REQ-HW-001 — USB-only power tree

**Requirement.** The product shall have one normal power input: USB 5 V SELV. The power tree shall protect and convert this input for controller/logic rails and shall not connect USB VBUS or a power-output rail directly to a test-bank endpoint. No battery or external test-bank power-input mode is permitted.

**Rationale.** A single bounded source simplifies fault analysis and avoids energizing the assembly under test.

**Planned verification.** Datasheet-backed schematic/net analysis, ERC, PCB cross-analysis, and continuity/power bench tests.

### REQ-HW-002 — Named test points

**Requirement.** The carrier shall provide labeled, accessible test points for USB input, each generated logic rail, ground, precheck reference/output, active-drive enable/control, status, and at least one representative channel on each bank.

**Rationale.** Bring-up and fault verification require probe access without relying on connector contacts.

**Planned verification.** Schematic/PCB inspection and assembly probe-access check.

### REQ-HW-003 — Bench protection and ESD

**Requirement.** Every externally touchable test-bank path shall use a documented current-limiting/protection network selected from manufacturer evidence, and external connectors shall receive ESD treatment appropriate to ordinary indoor bench handling. No protection rating may be described as permission for energized testing.

**Rationale.** Routine shorts and static handling are credible faults within intended use.

**Planned verification.** Datasheet review, fault calculation/simulation, schematic/PCB analysis, and controlled bench fault/ESD-plan review.

### REQ-MEC-001 — Main-board envelope

**Requirement.** The main PCB shall fit within 100 mm × 80 mm unless an approved requirements revision records connector-spacing evidence and updates enclosure/interface documents.

**Rationale.** The target keeps the bench device compact while allowing reviewable exceptions.

**Planned verification.** KiCad board-outline measurement and enclosure fit check.

### REQ-MEC-002 — Retained serviceable assembly

**Requirement.** The main board shall have four mounting points or equivalent positive retention. The enclosure shall open with common hand tools, shall not rely on adhesive for routine service, and shall retain clear access to USB, start/cancel, status, adapters, and recovery/debug provisions.

**Rationale.** The open-hardware product should be repairable and robust against connector loads.

**Planned verification.** Mechanical source inspection, assembly trial, and serviceability checklist.

### REQ-MEC-003 — Keyed replaceable adapters

**Requirement.** Bank connectors shall be polarized/keyed and visibly marked with bank, canonical position sequence, and pin-1/key landmark. Adapters shall be replaceable without soldering the main carrier.

**Rationale.** Replaceable keyed interfaces reduce reversal and connector-wear consequences.

**Planned verification.** Connector datasheet/drawing review, PCB/silkscreen inspection, and mating-cycle assembly check.

### REQ-ENV-001 — Indoor ordinary environment

**Requirement.** Specified operation shall be limited to a dry, non-condensing indoor bench within the validated temperature and supply ranges in the active limits record. No outdoor, wet, dusty-industrial, vehicle, or high-vibration rating shall be claimed.

**Rationale.** Environmental claims must match the eventual component and enclosure evidence.

**Planned verification.** Limits/datasheet review and release-document inspection.

### REQ-ENV-002 — Disconnected storage and fixture changes

**Requirement.** Instructions shall require the item under test to be disconnected before storage, transport, adapter changes, or connector reconfiguration. Adapter change shall invalidate any precheck token.

**Rationale.** Handling transitions are common opportunities for accidental external connection.

**Planned verification.** Documentation inspection and app/firmware state test.

### REQ-SRC-001 — Traceable critical-part selection

**Requirement.** Every electrically critical component shall have manufacturer, exact MPN, approved package/footprint, manufacturer datasheet, supplier/source evidence, lifecycle status, and selection rationale recorded in KiCad symbol properties or the pre-KiCad machine-readable handoff. Time-sensitive stock and price evidence shall include retrieval date and shall never be inferred.

**Rationale.** Safety and pin mapping depend on the exact physical part, not a generic function label.

**Planned verification.** BOM/property audit, datasheet cross-check, and sourcing evidence review.

### REQ-SRC-002 — Prototype cost target

**Requirement.** The planning target is USD 35–60 for one controller, carrier, first passive adapter, enclosure materials, ordinary USB cable, and fasteners, with a USD 75 ceiling excluding host computer, tools, shipping, tax, and specialized adapters. Until live quantity-specific evidence is cited, cost status shall be `unknown`, not estimated as achieved.

**Rationale.** A target guides selection without fabricating volatile commercial data.

**Planned verification.** Dated BOM pricing roll-up and scope inspection before prototype order.
