# PinPath rev-A candidate — bring-up checklist

Status: **not executed.** No PinPath carrier has been fabricated or assembled
as of this writing, so every "Actual" field below is intentionally blank and
every expectation is a datasheet-derived prediction, not a measurement. Do not
mark any row done without recording the instrument, conditions, firmware
commit, limits revision, and raw observation exactly as specified.

## Evidence rules (from `docs/verification-matrix.md`)

- Expectations below are `DOC`/`CALC` class (datasheet + static calculation).
- Recording a row converts it to `BENCH` and requires: hardware revision,
  firmware commit hash, limits revision, instrument make/model, setup,
  ambient conditions, raw observation, expected range, result, date.
- No row may be copied from simulation. Host-simulated protocol results live
  in `hardware/reports/integration-scenario-matrix-hostsim.json` and are
  `SIM` evidence, not bench evidence.
- Until step 0 completes and `hardware/selection/limits-rev-a.json` is
  updated to `validated: true` with this checklist as evidence, firmware must
  refuse scans. A firmware that scans with unvalidated limits is itself a
  bring-up failure.

## Step 0 — pre-power inspection (no instrument)

| # | Check | Expected | Actual |
|---|---|---|---|
| 0.1 | U1 castellations bridge-free under 10× | 0 bridges | |
| 0.2 | U2–U9 every pin wetted, no bridges | 0 bridges ×8 | |
| 0.3 | D1–D32 clamp orientation matches silkscreen | 32/32 | |
| 0.4 | D33–D40 pin-1 dots match silkscreen | 8/8 | |
| 0.5 | D41/D42 LED polarity correct | 2/2 | |
| 0.6 | J1/J2 keys oriented per silkscreen bank marking | 2/2 | |
| 0.7 | USB VBUS→3V3 path shorted check: <10 Ω VBUS-GND is a short, stop | open (module switching input) | |

## Step 1 — power-up without firmware interference (unpowered module)

Instruments: DMM. Conditions: USB cable only, no bank connectors populated.

| # | Measurement | Expected (datasheet/static basis) | Actual |
|---|---|---|---|
| 1.1 | USB VBUS at module | 4.75–5.25 V (USB 2.0 spec; Pico SC0915 input) | |
| 1.2 | 3V3 at module output | 3.0–3.63 V; static range from `limits-rev-a.json` | |
| 1.3 | REF3318 OUT (measure at U10) | 1.700–1.900 V (datasheet 1.8 V ±0.5 % initial ≪ provisional 1.7–1.9 band) | |
| 1.4 | Board supply current from USB | < 100 mA with firmware idle (RP2040 + 9 µA-class ICs; **prediction, unmeasured**) | |

## Step 2 — firmware boot and protocol handshake

Instruments: host with serial terminal. Firmware: commit recorded below.

| # | Action | Expected | Actual |
|---|---|---|---|
| 2.1 | Plug USB (module flashed) | CDC device enumerates | |
| 2.2 | Send `hello` | `hello_result`, `state: "idle_safe"`, revisions echoed | |
| 2.3 | All bank GPIO at rest (scope on TP7 drive-enable + TP10/TP11 endpoint nodes + spot-check mux outputs at series resistors) | high-impedance / no drive; logic low bias only | |
| 2.4 | Send `scan` without precheck | `error precheck_required`, state unchanged | |

Firmware commit: ______  Limits revision: ______

## Step 3 — precheck characterization (the gate for `validated: true`)

Current MVP `main.cpp` HAL is a fail-closed placeholder, so this step is
executed either with the analog front-end HAL built, or by direct ADC
manipulation on a debug build. Instrument: calibrated DMM plus a variable
low-voltage source **limited to ≤ 5 V and ≤ 1 mA** for injected-divisor work.
Inject only on single endpoints, one at a time — this characterizes the
detector; it is not permission for energized testing of user cables.

| # | Condition | Expected (from `limits-rev-a.json` static sweep) | Actual |
|---|---|---|---|
| 3.1 | All 32 endpoints floating, no injection | both phases track: low ≤ 0.2 V; high within ±0.2 V of measured reference | |
| 3.2 | Each endpoint tied to 3.3 V through 10 kΩ | detection on ≥1 phase, fail closed | |
| 3.3 | Each endpoint tied to 5.0 V through 10 kΩ | detection, fail closed | |
| 3.4 | Each endpoint tied to ±5 V through 10 kΩ | detection, fail closed | |
| 3.5 | Direct (0 Ω) injection ±1 V..±5 V single endpoint | detection, fail closed; note: >10 kΩ sources are outside the guaranteed detection model | |
| 3.6 | Injected voltage, worst-case clamp current (measure at D-series) | ≤ 97 µA pos / ≤ 464 µA neg (calculated, `limits-rev-a.json`) | |
| 3.7 | Driven endpoint shorted to GND (self-test mode) | drive current ≤ 367 µA (calculated) | |
| 3.8 | Token timing: precheck pass, wait 5.001 s, scan | `precheck_expired`, `idle_safe` | |
| 3.9 | Token single-use: one scan consumes token | second scan `precheck_required` | |
| 3.10 | Adapter swap after precheck | scan refused / token invalidated per app+fw gate | |

When 3.1–3.10 all pass with recorded instruments, update
`limits-rev-a.json`: `validated: true`, `firmware_scan_authorized: true`,
evidence reference to this filled checklist. Until then, scans remain refused.

## Step 4 — scan engine on known fixtures

Fixture: known-loopback adapter **continuity-verified by DMM first** (all 16
positions, documented per adapter numbering rules).

| # | Action | Expected | Actual |
|---|---|---|---|
| 4.1 | `self_test` loopback | 16/16 match, `pass: true`, `stable: true` | |
| 4.2 | Insert one open lead | that pair in `open`, `pass: false` | |
| 4.3 | Cross two pairs at the fixture | `crossover`, `pass: false` | |
| 4.4 | Short two pairs together | `short` merged group, `pass: false` | |
| 4.5 | Partially seated lead | `unstable` flag or open; never a clean pass | |
| 4.6 | Scan repeatability, 10 consecutive identical scans | identical `observed_groups` on all 10; record any edge seen-count variation | |
| 4.7 | Cancel mid-scan (host and, when wired, SW1) | `cancelled`, `complete: false`, GPIO safe (scope capture) | |
| 4.8 | USB unplug mid-scan | drive off within scan-loop bound, no latched drive (scope capture at TP7 + TP10/TP11) | |
| 4.9 | Reset mid-scan (RUN repressed / brownout sim) | boot returns `idle_safe`; scan refused until new precheck | |
| 4.10 | Injection during active scan (conditions like 3.3) | `fault unexpected_voltage`, nodes safe, token gone | |

Each row's raw frames saved as `docs/bringup/raw/<date>-<row>.jsonl` when
executed.

## Step 5 — limits validation and documentation

1. Fill this checklist completely (steps 0–4) with real instruments.
2. Update `limits-rev-a.json` thresholds/tolerance/temperature range from the
   recorded data; bump `limits_revision`.
3. Record supply current (1.4), fault currents (3.6/3.7), and repeatability
   (4.6) in the release notes.
4. Only then may the release manifest mark the board "bench characterized."

## Prohibited during bring-up

No mains, PoE, battery-pack, vehicle, medical, or any energized-source
injection beyond the ≤ 5 V / ≤ 1 mA single-endpoint divisor characterizations
above. Precheck detection capability is never a license to probe live wiring.
