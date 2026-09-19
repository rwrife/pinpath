# PinPath rev-A candidate — measurement and characterization plan

Status: **planned, not executed.** No assembled PinPath unit exists, so this
document defines exactly what will be measured, with what, and how the result
converts `hardware/selection/limits-rev-a.json` from `validated: false` to a
validated record. Until it is executed on real hardware, every electrical
number in the repository remains a datasheet-backed static calculation, and no
scan is authorized.

## Scope and vocabulary

Measurements are grouped so the release documentation can quote each with its
evidence class (see `docs/verification-matrix.md`):

| Group | Question | Evidence class when executed |
|---|---|---|
| M1 | Scan repeatability | BENCH |
| M2 | Precheck threshold behavior | BENCH |
| M3 | Fault current | BENCH (DMM/scope) |
| M4 | Supply current | BENCH |
| M5 | Known limitations list | DOC over M1–M4 |

Deliberately **out of scope** (and never to be quoted from this plan): cable
certification, insulation/hipot, impedance, bandwidth, precision resistance,
or any energized-source behavior beyond a single endpoint at ≤ 5 V through the
committed resistor network. The device is a de-energized-only mapper; this plan
characterizes its protection boundary, it does not extend it.

## Setup requirements (all groups)

- Assembled unit, hardware revision and firmware commit recorded.
- Bench DMM (documented model), USB inline power meter or DMM-in-series
  setup, 2-channel oscilloscope with current probe or sense-resistor method,
  calibrated low-voltage DC source with ≤ 1 mA series limit, decade box or
  0.1 %-tolerance resistors for divisor injection.
- Ambient: indoor dry bench, 20–30 °C, recorded per session.
- All injections are single-endpoint, referenced to board GND, and limited by
  the existing 10 kΩ series network. Injection above ±5 V or multi-endpoint
  simultaneous drive is prohibited by design (limits record) and is not a
  measurement target.

## M1 — scan repeatability

1. With the DMM-continuity-verified known-loopback adapter: 20 consecutive
   full scans (default 8 repetitions) after fresh prechecks.
   Pass: identical `observed_groups` and `classes` on all 20; any unstable
   flag is a finding, not a flake to average away.
2. Same with a 10-conductor known-good harness (profile built from DMM
   continuity).
3. Half-seated lead (back off one cavity 1 mm): record how often the result
   is `unstable` vs `open` vs (unwanted) clean pass. A clean pass on a
   half-seated conductor must be treated as a detection gap.
4. Record: firmware commit, limits revision, adapter revision, per-scan raw
   JSONL, summary table.

## M2 — precheck threshold behavior

Characterize the fail-closed boundary, matching the static sweep in
`limits-rev-a.json` (sources at −5, −1, 0, +1.8, +3.3, +5 V through 0 and
10 kΩ):

1. For each of the 32 endpoints, at least the full 6×2 source grid from the
   committed sweep on 4 representative endpoints (one per mux quadrant), and
   the 0 V/1.8 V/3.3 V subset on the remaining 28.
   Pass: every injected source fails at least one phase (precheck refuses).
2. Find the minimum detectable source impedance by decade box on one
   endpoint (expected to lose detection above ≈10 kΩ — the committed model
   does not promise detection of arbitrarily high-impedance sources; the
   measured crossover point becomes a documented limitation).
3. Reference health: verify REF3318 reading stays inside 1.7–1.9 V across the
   session; out-of-range sessions are void.
4. Token behavior at the bench: pass→5.001 s→scan rejected; single-use;
   adapter-change invalidation.

## M3 — fault current

All measured with the scope/DMM at the series network while the **board's own**
drive or an injected source is active, single endpoint only:

| Case | Calculated limit (`limits-rev-a.json`) | Measured |
|---|---|---|
| Endpoint injected +5 V (worst positive clamp path) | ≤ 96.97 µA | |
| Endpoint injected −5 V (negative clamp path) | ≤ 463.64 µA | |
| Driven endpoint shorted to GND | ≤ 366.67 µA | |
| Two opposing drives (scheduler normally forbids; forced via debug build) | ≤ 183.33 µA | |
| Series resistor worst-case dissipation | ≤ 2.13 mW vs 125 mW rating | |

Pass: measured ≤ calculated + instrument uncertainty, recorded with the
uncertainty stated. The debug-build row exists to verify the *hardware* bound;
the scheduler's one-drive invariant is proven in firmware tests, not by making
the device contend in normal operation.

## M4 — supply current

1. USB 5 V input current: boot, idle, mid-scan, fault-latched (inline meter,
   1 s averages). Compare against the < 100 mA design expectation; if higher,
   the excess is documented, not silently accepted.
2. 3V3 rail current at the module output (DMM µA range) for the same states.
3. Bank leakage: with the loopback adapter fitted and the board in
   `idle_safe`, measure endpoint-to-endpoint leakage on 4 positions; any
   reading that would change a >1 MΩ open judgement is a finding.

## M5 — known limitations record (what gets written into the release)

After M1–M4, the release documentation must state at least:

- measured repeatability rate and the half-seated detection gap (if any);
- the measured high-impedance source detection boundary (expected ≈10 kΩ,
  measured value governs);
- measured fault currents with instrument uncertainty;
- measured supply currents;
- the `U9.2` fanout stub and pour-island residuals from
  `hardware/PCB-layout-evidence.md` remain rev-A residuals until rev-B;
- explicit non-claims: not a certifier, not an insulation/hipot/impedance
  instrument, not for energized assemblies of any kind.

## Execution log

| Date | Session | Hardware rev | FW commit | Instruments | Result |
|---|---|---|---|---|---|
| — | none executed | — | — | — | plan only |
