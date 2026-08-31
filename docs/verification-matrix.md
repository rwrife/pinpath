# Requirement-to-verification matrix

This matrix separates evidence classes so static analysis or simulation is never presented as physical validation. A requirement closes only when its listed acceptance evidence exists for the relevant implementation/release revision.

## Evidence classes

| Code | Evidence class | Meaning |
|---|---|---|
| `DOC` | Static documentation inspection | Normative wording, boundaries, drawings, schema, traceability, terminology |
| `EDA` | KiCad/static hardware analysis | Editable source inspection, datasheet pin cross-check, ERC/DRC/analyzers, fabrication geometry inspection |
| `CALC` | Checked calculation | Versioned input assumptions, equations, worst-case/tolerance result, reviewer-reproducible output |
| `SIM` | Simulation | SPICE, logic/timing, or host model with source revision and fixtures; not physical evidence |
| `FW` | Firmware automated test/build | Host unit/property/parser test, target build, or static analysis |
| `APP` | App automated test/build | Unit/integration/accessibility/security/platform build |
| `BENCH` | Controlled physical bench evidence | Real assembled revision, instrument/setup/conditions/raw results recorded |
| `FIELD` | Later supervised field observation | Informational post-bench use; never substitutes for required bench or certification evidence |

The report-level `evidence_context` enum is closed and maps to these classes as follows: `host_simulation` → `SIM`; `bench` → `BENCH`; `field_observation` → `FIELD`; `device_observation` → no acceptance-evidence class until a controlled bench record supplies the required hardware revision, instruments, setup, conditions, and raw observations.

## Matrix

| Requirement | Primary acceptance evidence | Supplemental evidence | Milestone/owner |
|---|---|---|---|
| REQ-SCP-001 | DOC + FW + APP | BENCH lockout workflow | #1, #5, #6, #7 |
| REQ-SCP-002 | DOC release-package audit | APP terminology audit | #1, #6, #7 |
| REQ-SCP-003 | DOC architecture/permissions audit + APP offline test | BENCH supervised workflow | #1, #6, #7 |
| REQ-FUN-001 | EDA endpoint/pin audit + FW endpoint-table test + APP matrix test | BENCH assembled continuity audit | #3, #4, #5, #6, #7 |
| REQ-FUN-002 | FW state test + APP workflow test | BENCH observation | #5, #6, #7 |
| REQ-FUN-003 | FW classifier unit/property tests + APP fixtures | SIM connectivity model + BENCH loopback | #5, #6, #7 |
| REQ-FUN-004 | FW classifier unit/property tests + APP fixtures | SIM + BENCH known-fault fixtures | #5, #6, #7 |
| REQ-FUN-005 | FW scheduler/boundary tests | SIM timing + BENCH timing | #5, #7 |
| REQ-FUN-006 | FW cancellation tests + APP protocol tests | BENCH GPIO observation | #5, #6, #7 |
| REQ-SAF-001 | EDA schematic/static review + FW register-state tests | SIM reset/fault + BENCH impedance/GPIO | #2, #3, #5, #7 |
| REQ-SAF-002 | EDA datasheet-backed default-state analysis + FW startup test | SIM power/reset + BENCH powered/off/reset | #2, #3, #5, #7 |
| REQ-SAF-003 | FW scheduler invariant/property tests + EDA pin-mux audit | SIM + BENCH multi-channel capture | #3, #5, #7 |
| REQ-SAF-004 | EDA precheck topology review + CALC tolerance analysis + FW injected-input tests | SIM + BENCH swept-voltage | #2, #3, #5, #7 |
| REQ-SAF-005 | FW state/timing/disconnect/reset tests | APP fixture + BENCH disconnect/reset | #5, #6, #7 |
| REQ-SAF-006 | DOC limits-schema validation + manufacturer-backed CALC | SIM + FW compatibility + BENCH characterization | #2, #5, #7 |
| REQ-SAF-007 | FW fault/parser/reset tests | SIM + APP fault fixtures + BENCH fault matrix | #5, #6, #7 |
| REQ-SAF-008 | DOC manifest/schema test + FW simulated fixture faults | EDA adapter mapping + BENCH known adapter | #2, #4, #5, #7 |
| REQ-SAF-009 | DOC protocol/API audit + FW negative tests | APP fuzz/interoperability tests | #5, #6 |
| REQ-IFC-001 | DOC/schema/source lint + FW/APP endpoint tests | EDA silkscreen + BENCH label inspection | #1, #4, #5, #6, #7 |
| REQ-IFC-002 | DOC drawing/manifest/schema audit + EDA connector cross-check | BENCH adapter continuity | #2, #3, #4, #7 |
| REQ-IFC-003 | FW + APP parser boundary/property tests | DOC memory review + interoperability test | #5, #6 |
| REQ-IFC-004 | DOC schema audit + FW/APP cross-version tests | BENCH compatibility smoke test | #5, #6, #7 |
| REQ-IFC-005 | EDA schematic/net/DRC/cross-analysis | BENCH continuity/power isolation | #3, #4, #7 |
| REQ-REP-001 | FW golden classifier vectors + APP rendering tests | DOC terminology audit + BENCH fixture cases | #5, #6, #7 |
| REQ-REP-002 | FW/APP schema and serialization round-trip tests | DOC export inspection + BENCH metadata audit | #5, #6, #7 |
| REQ-REP-003 | FW report tests + APP accessibility/export tests | BENCH result inspection | #5, #6, #7 |
| REQ-DAT-001 | APP storage/migration/backup/offline tests | DOC privacy audit | #6 |
| REQ-DAT-002 | APP hostile-text/export tests | DOC manual export inspection | #6 |
| REQ-ACC-001 | DOC accessibility inspection + EDA legends review + APP status tests | BENCH hardware cue inspection | #3, #4, #6, #7 |
| REQ-ACC-002 | APP automated accessibility and keyboard tests | DOC cross-platform screen-reader/manual plan | #6, #7 |
| REQ-HW-001 | EDA datasheet-backed power/net analysis, ERC/DRC/cross-analysis | BENCH continuity and rail measurements | #2, #3, #4, #7 |
| REQ-HW-002 | EDA schematic/PCB probe-access inspection | BENCH assembly access check | #3, #4, #7 |
| REQ-HW-003 | EDA datasheet/schematic/PCB review + CALC fault analysis | SIM + BENCH controlled fault/pre-compliance plan | #2, #3, #4, #7 |
| REQ-MEC-001 | EDA board-outline measurement | BENCH enclosure fit | #4, #7 |
| REQ-MEC-002 | DOC mechanical-source/service checklist | BENCH assembly/service trial | #4, #7 |
| REQ-MEC-003 | EDA connector drawing/silkscreen review | BENCH keyed fit/mating-cycle observation | #2, #4, #7 |
| REQ-ENV-001 | DOC limits/datasheet and release audit | BENCH only within validated environment | #2, #7 |
| REQ-ENV-002 | DOC instructions audit + FW/APP adapter-change test | BENCH workflow observation | #1, #5, #6, #7 |
| REQ-SRC-001 | DOC BOM/property/datasheet/sourcing audit | EDA footprint/property cross-check | #2, #3, #7 |
| REQ-SRC-002 | DOC dated BOM pricing roll-up and scope audit | None; volatile commercial evidence must be refreshed | #2, #7 |

## Physical-evidence rules

- `BENCH` evidence records actual hardware/adapter revisions, firmware commit, limits revision, instrument make/model or calibrated fixture, setup, environmental conditions, raw observations, expected range, result, and date.
- Host-injected matrices, mocked serial fixtures, KiCad analyzers, and SPICE are `SIM`/automated evidence, not bench results.
- A fabricated but untested assembly is not bench-validated.
- `FIELD` observations begin only after applicable bench gates; they never create cable-certification, live-test, safety, hipot, insulation, impedance, bandwidth, or precision-resistance claims.
- Prohibited high-energy use cases are verified by documentation/design-boundary inspection, not by intentionally applying mains, PoE, battery-pack, vehicle, or medical-system energy.
