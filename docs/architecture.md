# PinPath MVP architecture and semantics

Status: **normative architecture baseline** for issue #1. It defines boundaries and behavior; it does not claim that hardware, firmware, app, or bench validation exists.

## Safety boundary

PinPath is a USB-powered continuity mapper for fully disconnected, de-energized passive assemblies. Protection and precheck reduce damage risk but do not authorize live testing. Never connect mains, PoE, a battery or battery pack, powered USB through a test bank, vehicles, medical or life-safety wiring, or any energized circuit. PinPath makes no cable certification claim. The prohibitions in REQ-SCP-002 apply to every layer.

The trusted safety boundary is the device hardware plus firmware state machine. The desktop app is an untrusted command source. The operator remains responsible for disconnecting the assembly; the precheck is a fail-closed secondary guard, not proof of safety.

## System blocks and power tree

```text
host USB port
  └─ USB 5 V SELV
      └─ input protection / filtering
          ├─ controller-module or carrier regulator → logic rail(s)
          │   ├─ RP2040-class controller / USB CDC
          │   ├─ status + start/cancel
          │   └─ precheck measurement/reference
          └─ protected, current-limited stimulus/sense front end
              ├─ Bank A: A:01 … A:16
              └─ Bank B: B:01 … B:16

SWD/local recovery ── controller only; no test-bank power path
Banks ── replaceable passive adapters ── de-energized cable/harness
```

USB VBUS and logic rails never connect directly to an exposed bank endpoint. The front end is the only electrical path from controller logic to the test-bank boundary. Exact topology and limits are deferred to manufacturer-backed selection in issue #2 and captured in the required limits record.

## Canonical endpoints and connector orientation

- Logical endpoints are exactly `A:01`–`A:16` and `B:01`–`B:16`.
- A canonical endpoint is not a raw RP2040 GPIO, connector footprint pad, wire color, or cable function.
- The two-digit, uppercase form is the only form accepted on the wire or in saved profiles.
- Main-board and adapter silkscreen use Bank + canonical position and a pin-1/key landmark.
- Vendor connector numbering is not assumed. Every adapter manifest maps canonical endpoint → reference designator → manufacturer pin number → mating-face orientation → key/pin-1 landmark → user-visible label.
- Drawings state their viewing direction. “Mating face” means looking into the connector face that receives its mate, with the documented key landmark in the documented orientation.

This preserves stable profile names if MCU pins, connectors, or board revisions change.

## Test-bank and adapter boundary

The main carrier ends at two polarized 16-position bank connectors. Adapters are passive, revisioned, replaceable fixtures. The first set comprises a numbered flying-lead adapter and a known-loopback self-test adapter. An adapter must not inject power, translate voltage, identify a connector automatically, or bypass front-end protection.

A machine-readable adapter manifest contains:

- schema and adapter revision;
- compatible hardware revision(s);
- bank and canonical endpoint mapping;
- connector manufacturer/MPN and physical pin number;
- mating-face orientation and key/pin-1 landmark;
- expected loopback groups and expected-isolated endpoints for self-test.

Changing or declaring a different adapter invalidates a precheck token.

## Safe condition and scan strategy

The bank safe condition is all active stimulus/enable paths disabled and all MCU scan pins input/high-impedance with pulls off. Only passive bias/protection and high-impedance precheck sensing may remain. Hardware defaults must preserve this condition without running firmware.

A scan is break-before-make:

1. Enter and verify the safe condition.
2. Select one canonical endpoint in software only.
3. Enable at most its single current-limited stimulus path.
4. Sample all endpoints through bounded sense paths.
5. Disable stimulus and verify no active-drive bit remains.
6. Continue to the next endpoint or return safe on cancel/fault.

No code path may expose raw GPIO drive commands. A scheduler invariant enforces active-drive cardinality `0..1` and equal opportunities per endpoint in a complete scan.

## Precheck and limits record

Precheck runs with active stimulus disabled and evaluates all 32 endpoints plus measurement-reference health. It fails closed on any missing, saturated, out-of-range, or inconsistent reading.

A pass creates a single-use token that expires after 5 seconds and is bound to the connection session, hardware revision, limits revision, and adapter manifest. The next self-test/scan consumes it. Disconnect, reset, cancel, fault, watchdog, adapter change, incompatible command, or expiry invalidates it.

The versioned limits record is the only source for part-dependent electrical thresholds. It records precheck thresholds/tolerance, drive/injection limits, stimulus level/time, continuity decision thresholds, and environmental range, together with validation status and evidence references. Firmware refuses scans with an absent, invalid, unvalidated, or incompatible record. No value in this architecture document substitutes for issue #2 calculations or issue #7 measurements.

## State machine and recovery

```text
BOOT/RESET
   └─ enforce safe ──> IDLE_SAFE
                         ├─ precheck pass ──> ARMED (single-use, ≤5 s)
                         │                     ├─ self_test ──> CLASSIFY ──> IDLE_SAFE
                         │                     └─ scan ───────> CLASSIFY ──> IDLE_SAFE
                         └─ precheck fail ──> FAULT_SAFE

Any active state -- cancel/disconnect/reset/watchdog/invariant/voltage fault --> SAFE
SAFE + reportable recoverable fault --> FAULT_SAFE
FAULT_SAFE -- clear allowed cause + new precheck --> ARMED
```

| Event | Required bank action | Result/report | Recovery |
|---|---|---|---|
| Power-up, reset, brownout | Preserve hardware-default safe; firmware verifies safe | No scan result | Reach `IDLE_SAFE`, then new precheck |
| Failed/stale precheck | Stay safe | Stable fault reason; no pass | Remove cause, run new precheck |
| Local or host cancel | Disable drive before acknowledgement | `cancelled`, partial/non-passing | New precheck |
| Host USB disconnect | Disable drive immediately through transport/state handling | Partial/non-passing if reporting later is possible | New connection + precheck |
| Watchdog/internal invariant | Hardware/boot default safe | Fault after reboot when retained reason exists | New precheck after diagnostics |
| Malformed/oversized/incompatible command | Stay safe; if armed, invalidate the token and leave `ARMED` | Bounded protocol error | Correct command; run a new precheck when the armed token was invalidated or the state faulted |
| Unexpected voltage during scan | Disable drive and latch fault-safe | Partial/non-passing voltage fault | Physical disconnect/removal + new precheck |
| Self-test mismatch/unstable fixture | Disable drive | Self-test failed; scan unavailable | Repair/reseat fixture + new precheck |

The host cannot clear a non-recoverable hardware fault or override a precheck.

## Connectivity model

### Normalized groups

Connectivity is represented as disjoint, sorted groups of canonical endpoints. Endpoints within one group were mutually connected under the continuity decision in the active limits record. Groups are sorted lexically and duplicates are invalid. Isolated endpoints are retained as one-member observed groups so unknown-map output covers all 32 positions.

An expected profile contains groups of two or more endpoints. Endpoints not in an expected group are expected isolated. This representation supports ordinary point-to-point cables, fan-out/splice harnesses, intentional same-bank connections, and unused positions without assuming that every conductor joins Bank A to Bank B.

### Unknown-map mode

Unknown-map mode reports observed groups and repetition evidence only. It does not label a connection correct, crossed, or shorted because no expected intent exists.

### Expected-map mode and precedence

The classifier uses complete, stable observations only for a pass:

1. **unstable** — an endpoint relation is present in some usable repetitions and absent in others. The affected expected/observed groups cannot pass.
2. **crossover** — for two-endpoint expected groups, the affected endpoints form a complete stable bijection of two-endpoint observed groups, but one or more counterparts are permuted. No observed group may have more than two members or include an expected-isolated endpoint. Each permutation cycle is reported once so a swap is not double-counted as unrelated opens or shorts.
3. **short** — one stable observed group merges endpoints from two or more distinct expected groups, contains more than two endpoints, or connects any expected-isolated endpoint, except for a complete bijective crossover already classified by step 2.
4. **open** — members of one expected group are split across observed groups or isolated and are not wholly explained by a classified crossover cycle.
5. **matched** — an expected group exactly equals one stable observed group and is unaffected by higher-precedence findings.
6. **not_evaluated** — scan cancelled, faulted, incomplete, incompatible, or lacks validated limits/evidence.

A multi-node observed group that merges intended nets is always a short, not a set of crossovers. A lone wrong pair that does not form a complete bijection leaves the displaced expected endpoints open and is not promoted to a crossover. A missing connection may coexist with an unrelated short; reports preserve all affected endpoints but calculate no single “pass” if any non-matched class exists.

### Repetitions and stability

Default repetitions are 8; accepted range is 3–64. For each undirected pair, an observation count of `0` means stably disconnected, `N` means stably connected, and `1..N-1` means unstable. A complete result provides equal stimulus/sample opportunities for every endpoint. Cancel/fault yields partial evidence and `not_evaluated`, never pass.

## Report semantics and quality flags

Each result records normalized expected/observed groups, class details, repetition counts, completion, revisions, and exactly one evidence context from `host_simulation`, `device_observation`, `bench`, or `field_observation`. `device_observation` is a real-device result without the instrument/setup record required for controlled `bench` evidence and must not be presented as validation. The independent required quality flags are:

- `precheck_passed`
- `self_test_passed` (false/not applicable is explicit by mode)
- `complete`
- `stable`
- `limits_validated`
- `revision_compatible`

A false flag carries a stable reason code. Expected-map pass requires every applicable flag true and every expected group `matched`. UI and exports show text/icon labels in addition to color. “Pass” means profile comparison passed under the recorded limits; it never means electrically safe, standards-compliant, or cable-certified.

## USB, debug, privacy, and accessibility boundaries

USB CDC carries bounded protocol data and USB 5 V SELV. Debug is a local controller-only recovery interface. Neither exposes a bank-power command. There is no Wi-Fi, Bluetooth, cloud service, shell, remote listener, or application-protocol firmware update.

The app stores profiles/reports locally and requests serial or file access only after user action. All device/user text is untrusted. Connector and result presentation uses canonical numbers and textual class/status equivalents; keyboard, screen-reader, scalable-text, high-contrast, focus, and reduced-motion requirements are normative.

## Requirement ownership and downstream handoff

- Issue #2 selects exact parts and creates the validated limits/evidence handoff.
- Issue #3 implements and cross-checks the editable schematic and source-of-truth BOM.
- Issue #4 implements physical layout/adapters and fabrication inspection.
- Issues #5 and #6 implement this state/protocol/report contract.
- Issue #7 records physical measurements; until then all results remain static analysis, simulation, or host-test evidence only.
