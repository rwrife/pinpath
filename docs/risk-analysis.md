# PinPath misuse and fault analysis

Status: architecture-stage analysis for disconnected, de-energized passive assemblies. It identifies required controls and verification; it is not a quantitative safety certification, FMEA approval, or evidence that hardware survived a fault.

## Rating convention

- **Severity:** `S3` potential equipment damage or hazardous misuse outside intended scope; `S2` device/fixture damage or misleading result; `S1` interrupted use with visible non-passing result.
- **Exposure:** `E3` credible during ordinary setup/use; `E2` occasional fault; `E1` unusual/compound fault.
- **Residual disposition:** the required safe outcome after architecture controls. Numeric probability is intentionally not invented before implementation and bench data.

## Misuse and fault table

| ID | Misuse/fault and initiating condition | Effect without controls | S/E | Prevent/detect controls | Required response and recovery | Planned evidence |
|---|---|---|---|---|---|---|
| RISK-001 | Energized cable or harness connected, including powered USB on a bank lead | Back-powering, excessive clamp/GPIO current, device/host damage; protection could be mistaken for permission | S3/E3 | Prominent prohibition; disconnected-assembly acknowledgement; all-endpoint fail-closed precheck; current-limited front end; no host override | Keep/return all nodes safe, latch voltage fault, no scan; operator disconnects all sources and performs a new precheck | Datasheets, tolerance simulation, injected-ADC tests, swept-voltage bench test |
| RISK-002 | Mains, PoE, battery pack, vehicle, medical/life-safety, or unknown live wiring | Voltages/energy beyond design domain; shock/fire/equipment risk | S3/E2 | Explicit exclusion in device/app/assembly/release text; connector/adapters not marketed for these domains; no compliance claims | Do not connect or test. Precheck/protection is not credited as a safe control for prohibited energy | Documentation audit only; no hazardous bench injection |
| RISK-003 | Two actively driven GPIO/front-end nodes shorted by cable or fault | Output contention and overcurrent | S2/E3 | Hardware current limit; active-drive cardinality ≤1; break-before-make; hardware safe defaults | Disable current drive, report short/non-pass, return safe; new precheck | Worst-case calculations, scheduler invariant test, short simulation, controlled low-energy bench fault |
| RISK-004 | One driven node joins many sense nodes (multi-node short) | Aggregate clamp/bias current or misleading map | S2/E2 | Front-end aggregate-current calculation; one active drive; bounded dwell; sample all endpoints | Disable after bounded sample, report one merged short group, return safe | SPICE where useful, classifier vectors, multi-short bench fixture |
| RISK-005 | Externally driven voltage appears after precheck or during scan | Stale authorization and excessive current | S3/E2 | Single-use ≤5 s precheck token; token invalidation; monitor/precheck capability during scan if selected topology supports it; current limiting | Immediate safe transition and voltage fault; partial/non-passing result; new physical setup and precheck | State tests, timing tests, swept/step voltage bench test within safe lab limits |
| RISK-006 | Adapter reversed, wrong revision, or wrong bank | Systematic crossover/short report; possible connector stress | S2/E3 | Polarized connectors; bank/position/pin-1 markings; revisioned manifest; self-test; compatibility gate | Reject incompatible manifest or fail self-test; never scan cable under ambiguous fixture | Drawing/manifest review, reversed-fixture host test, physical keyed-fit/continuity check |
| RISK-007 | Connector wear, contamination, partially seated lead, or broken adapter conductor | False open or intermittent result | S2/E3 | Replaceable adapter; known-loopback self-test; repeated observations; unstable quality flag; service guidance | Non-pass self-test or mark unstable/open; reseat/replace adapter and re-precheck | Repetition/classifier tests, self-test fault fixtures, later mating-cycle observations |
| RISK-008 | ESD at exposed bank/USB/control connector in ordinary bench handling | Reset, latent damage, corrupted result | S2/E2 | Manufacturer-backed ESD/protection; grounding/return layout; enclosure and handling guidance; reset-safe defaults | Reset/fault returns nodes safe; discard partial result; inspect and re-precheck | Datasheet/layout review, EMC analysis, controlled pre-compliance plan; no immunity claim without testing |
| RISK-009 | USB host disconnect, cable removal, suspend, or transport failure during scan | Firmware might continue driving; app may save incomplete result | S2/E3 | Device-owned watchdog/state timing; disconnect event; bounded scan; no host-owned raw drive | Disable stimulus, mark partial/non-passing when reportable; reconnect and precheck | Firmware transport-loss test, app fixture test, bench disconnect observation |
| RISK-010 | Firmware reset, watchdog, brownout, crash, or bootloader entry during scan | Pin modes/outputs may change unpredictably | S2/E2 | Hardware drive-enable defaults safe; scan GPIO reset state reviewed; boot establishes safe before commands | Hardware preserves safe; retained reason where possible; new precheck after reboot | Datasheet/schematic review, reset simulation, reset/brownout bench capture |
| RISK-011 | Cancel during any precheck/self-test/scan/classify phase | Residual stimulus or ambiguous result | S2/E3 | Cancel is a state transition; drive disable precedes acknowledgement; partial-result flag | Return safe then emit `cancelled`; require new precheck | Cancellation test at every scheduler boundary; GPIO bench observation |
| RISK-012 | Malformed, oversized, deeply nested, duplicated, replayed, out-of-order, or incompatible protocol input | Memory exhaustion, invalid transition, stale command, unsafe drive | S2/E3 | 32,768-byte/depth/string/array bounds; strict schema/version/id/state validation; no shell; no raw GPIO API | Reject before state change; stay/return safe; bounded error without echoing hostile data | Parser property/fuzz tests, protocol fixtures, memory review |
| RISK-013 | Stuck drive-enable component, solder bridge, wrong footprint/pin map, or assembly defect | Safe software state does not make endpoint high impedance | S2/E2 | Exact MPN/package/pin verification; hardware default topology; ERC/DRC/cross-analysis; self-test; named test points | Self-test/precheck fault where detectable; do not scan; diagnose/rework | Datasheet pin audit, KiCad mapping review, manufacturing inspection, safe-state bench measurement |
| RISK-014 | Precheck sensor/reference open, shorted, saturated, or out of calibration | External voltage falsely reads safe | S3/E2 | Reference/self-diagnostic range; all samples required; tolerance record; missing/out-of-range fails closed | Precheck fault, no token, remain safe until repair and validation | Fault-tree calculation, simulation, injected ADC/reference tests, bench fault injection |
| RISK-015 | Incorrect expected profile, duplicate endpoint, impossible group, or wrong adapter manifest | False pass/fail or confusing crossover | S2/E3 | Canonical schema; disjoint-group validation; revision compatibility; explicit preview; profile tests | Reject invalid profile before token consumption/scan; preserve prior data | Schema/property tests, app validation/accessibility tests |
| RISK-016 | Firmware/app/hardware/limits revisions disagree | Wrong pin map, threshold, capability, or parser semantics | S2/E2 | `hello_result` revisions; compatibility table; token binding; result metadata | Reject operation without drive; update matching component; new precheck | Cross-version matrix tests and release-manifest audit |
| RISK-017 | App exits/crashes or filesystem export fails | Device state uncertainty or corrupt/missing report | S1/E2 | Device remains safety authority; atomic local storage; explicit export; bounded scan | Device returns safe on disconnect/timeout; app marks transaction incomplete and preserves recoverable data | App crash/storage tests, transport-loss tests |
| RISK-018 | Status conveyed by color alone or connector numbering is unreadable/ambiguous | Misconnection or missed fault by user | S2/E3 | Text/number/icon/pattern cues; distinct ready/fault non-color cues; tactile/key landmark; accessible matrix text | Block workflow when status unavailable; never infer pass from color | Accessibility automation, keyboard/screen-reader plan, hardware legend inspection |
| RISK-019 | User changes adapter or wiring after passed precheck | Precheck no longer represents setup | S3/E3 | Instructions; 5-second single-use token; adapter-change invalidation; scan begins promptly | Expired/invalid token prevents scan; require new precheck | State timing tests, app flow test, bench setup observation |
| RISK-020 | Report is treated as cable certification or proof of electrical safety | Unsafe decision based on limited continuity evidence | S3/E2 | Narrow vocabulary; evidence type and limits revisions; explicit non-certification statements in UI/export | Report only profile comparison/non-pass observations; no safety verdict | Terminology and release-package audit |

## Fault containment principles

1. **Fail safe:** uncertainty, missing data, incompatible revisions, invalid input, or self-diagnostic failure never authorizes stimulus.
2. **Device-enforced:** the app can request but cannot override precheck, limits, state, or raw drive.
3. **Hardware-backed:** reset/unpowered defaults do not depend on application code.
4. **Bounded energy:** one current-limited drive, break-before-make, bounded dwell and scan duration.
5. **Evidence separation:** static analysis, simulation, host tests, bench measurements, and field observations are labeled independently.
6. **No prohibited fault testing:** mains, PoE, battery-pack, vehicle, medical, and other high-energy exclusions are handled by prohibition and design boundary, not hazardous injection tests.

## Open evidence gates (not open requirements)

The architecture requirement is frozen, but these implementation values/evidence remain intentionally pending:

- exact precheck thresholds, tolerances, stimulus voltage/current, continuity thresholds, and temperature range — issue #2 limits record;
- exact controller/front-end/protection/connectors and pin mappings — issues #2/#3;
- physical layout/ESD/return paths and adapter keying — issue #4;
- firmware/app test results — issues #5/#6;
- actual threshold, fault-current, reset, timing, and repeatability measurements — issue #7 on fabricated hardware.

Until those gates close, no text may describe PinPath as electrically validated, physically tested, certified, or safe for energized use.
