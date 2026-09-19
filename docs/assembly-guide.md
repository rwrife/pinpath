# PinPath rev-A candidate — assembly guide

Status: **pre-fabrication documentation.** No PinPath board has been fabricated,
assembled, or tested. Every step below is written for the rev-A candidate board
described by the committed KiCad sources; nothing here has been validated on a
physical unit. Photo/render placeholders are explicitly marked until real media
exists.

## Safety boundary (read first)

PinPath is for **disconnected, de-energized passive cables and harnesses only**.
Never connect mains, PoE, a battery or battery pack, powered USB through a test
bank, vehicles, medical or life-safety wiring, or any energized circuit. PinPath
is not a cable certifier, insulation tester, hipot tester, precision ohmmeter,
or protective instrument. Protection circuitry reduces ordinary fault stress; it
never authorizes prohibited live testing. The board silkscreen carries the same
prohibition.

## What you are building

One two-layer carrier board (96.05 × 76.05 mm) that contains:

| Block | Reference(s) | Part |
|---|---|---|
| Controller module (USB power, RP2040, 3V3) | U1 | Raspberry Pi Pico `SC0915`, castellated, hand-solder |
| Stimulus/sense muxes (8 × 8-channel) | U2–U9 | TI `TMUX1108PWR` (TSSOP-16) |
| Voltage reference (precheck/ADC) | U10 | TI `REF3318AIDBZR` (SOT-23-3) |
| Endpoint series limit resistors (10 kΩ) | R1–R32 | 0805, 1 % |
| Endpoint bias resistors (100 kΩ, plus 1 kΩ bias rail) | R33–R78 | 0805, 1 % (R75/R77/R78 = 1 kΩ; R33–R74/R76 = 100 kΩ) |
| Endpoint rail clamps (dual series diodes) | D1–D32 | Nexperia `BAS70-04,215` |
| Endpoint ESD arrays (4-channel) | D33–D40 | TI `TPD4E1U06DCKR` (SC70) |
| Status LEDs (READY/FAULT, text-labelled) | D41, D42 | see BOM |
| Bank connectors (16-position, keyed) | J1 (Bank A), J2 (Bank B) | Molex `43045-1600` Micro-Fit 3.0 header |
| Debug header (SWD, controller-only) | J3 | Samtec `FTSH-105-01-L-DV-K`, 1.27 mm |
| Start/cancel control | SW1 | see BOM |
| Test points | TP1–TP12 | project-local micro test points (map below) |

TP1–TP12 net map (from the committed board):

| Test point | Net | Use |
|---|---|---|
| TP1 | VBUS | USB 5 V check |
| TP2 | +3V3 | module regulator output |
| TP3 | GND | reference ground |
| TP4 | ADC_REF_1V8 | REF3318 output / ADC diagnostic |
| TP5 | BIAS | two-phase precheck bias node |
| TP6 | STIM | stimulus node |
| TP7 | DRV_A_LO_EN | Bank-A drive-enable |
| TP8 | READY_LED | READY drive line |
| TP9 | FAULT_LED | FAULT drive line |
| TP10 | A:01_NODE | Bank A position 01 endpoint node |
| TP11 | B:01_NODE | Bank B position 01 endpoint node |
| TP12 | RUN | module RUN/resets line |

Exact references, values, packages, and MPNs are authoritative in
`bom/bom.csv` (exported from the schematic symbol properties). This table is a
summary, not a substitute.

Non-schematic items (mating housings, crimp contacts, debug probe, cables,
enclosure) are tracked in `bom/non-schematic-items.csv`.

## Tools and conditions

- Temperature-controlled iron with a fine tip, flux, solder wick, and a
  no-clean flux pen for castellated rework.
- Stereo microscope or 10× loupe (TSSOP-16 and 1.27 mm header inspection).
- Bench DMM only (used on the **board**, never on an energized assembly under
  test). No other instruments are required for assembly.
- Dry, static-controlled bench with a grounded wrist strap.

## Assembly order (hand assembly)

1. **Stencil and paste (recommended) or careful hand soldering.** If reflowing:
   apply paste with a framed stencil, place parts in the order below, reflow to
   the paste and component datasheet profiles. If hand soldering: solder one
   joint per part, verify alignment under magnification, then flow the
   remaining pads.
2. **Small passives first** — R1–R78, C1–C9, D1–D40 (mind D1–D32 clamp
   orientation and D33–D40 pin-1 dot; a reversed clamp breaks the protection
   function and is a known assembly risk).
3. **U2–U9 TSSOP muxes** — drag-solder with flux and wick; inspect every pin
   for bridges (this is the densest hand-solder step on the board).
4. **U10 reference and D41/D42 LEDs** — mind LED polarity.
5. **SW1, TP1–TP12** (TP4–TP7 are the analog/drive-enable bring-up points; TP10/TP11 expose the A:01/B:01 endpoint nodes).
6. **J3 SWD header** (1.27 mm; align the key notch).
7. **J1/J2 bank connectors** — through-hole; check the latch/key orientation
   against the silkscreen before soldering. The silkscreen marks bank letter
   and position numbering.
8. **U1 Pico module last.** The module is supplied with headers unpopulated;
   do **not** socket it (the design assumes a soldered castellated mount).
   Tin the board pads, position the module square to the courtyard, tack two
   diagonal corners, then flow all castellations. Inspect for bridges and
   tombstones.

> ⚠️ Do not plug in USB until step "First power-up" below, and only after a
> visual bridge inspection of U1, U2–U9, and J1/J2.

- **[PHOTO PLACEHOLDER]** soldered top side, all blocks labelled
- **[PHOTO PLACEHOLDER]** soldered bottom side
- **[RENDER]** 3-D renders of the *unpopulated* candidate exist at
  `hardware/fab-out/renders/pinpath-top-20260919.png` and
  `pinpath-bottom-20260919.png`; they document component outlines and silk,
  not an assembled unit.

## Pinout and wiring diagrams (visual placeholders)

Canonical endpoints are exactly `A:01`–`A:16` and `B:01`–`B:16`
(`docs/architecture.md`). Connector pad numbering, mating-face view direction,
and the key landmark are defined by the adapter manifest
(`hardware/adapters/known-loopback/adapter-manifest.json`) and the board
silkscreen; vendor cavity numbering is never assumed.

- **[DIAGRAM PLACEHOLDER]** carrier top with J1/J2 cavity numbering overlay
  (to be generated from the fab drawing once a fab package is reviewed)
- **[DIAGRAM PLACEHOLDER]** J3 SWD pinout matched to the SC0889 probe cable
  (cable not yet selected; see `bom/non-schematic-items.csv`)
- **[WIRING PLACEHOLDER]** flying-lead adapter build: 2 × Molex 43025-1600
  housings + 43030-0007 crimp contacts, one lead per position, position
  numbering printed on heat-shrink sleeves per the manifest mapping

## Adapter numbering rules

- Every adapter is passive. It may not inject power, translate voltage, or
  identify itself electrically.
- Each position label is `A:nn` or `B:nn` and must match the manifest mapping
  endpoint → reference designator → manufacturer pin number → mating-face
  view → key landmark.
- The known-loopback self-test adapter wires `A:01↔B:01` … `A:16↔B:16`
  one-to-one (16 groups), per
  `hardware/adapters/known-loopback/adapter-manifest.json`.
- After building any adapter, run continuity position-by-position with a DMM
  **before** it is ever plugged into PinPath, and record the result in the
  bring-up log. The first loopback harness is unvalidated until this is done.

## Programming the firmware

Requirements: USB-C/micro-USB data cable (the board's USB is micro-B via the
Pico module), a host running the companion app or any serial terminal.

1. Build the UF2 per `firmware/README.md` (pinned Pico SDK 2.0.0).
2. Hold **BOOTSEL** on the module, plug USB in, release. The module enumerates
   as a USB drive (`RP2040`).
3. Copy `pinpath_firmware.uf2` to the drive. The board reboots into PinPath
   firmware.
4. Verify with `hello` over USB CDC; expect `hello_result` reporting
   `hardware_revision: "pinpath-rev-a-candidate"` and `state: "idle_safe"`.

## Recovery

- **Application firmware lock-up:** BOOTSEL re-flash as above (the bootloader
  is ROM-resident and always recoverable over USB).
- **Firmware bricks flash content:** BOOTSEL still works; re-flash.
- **SWD access (controller-only; never a path to the banks):** 10-pin header
  J3 (SWDIO/SWCLK/GND plus VTREF **sense only** — do not power the debugger
  from VTREF). Candidate probe: Raspberry Pi `SC0889` with an adapter cable
  still to be selected. TP4–TP7 (reference/BIAS/STIM/drive-enable) and
  TP10/TP11 (endpoint nodes) provide scope access for bring-up.
- A board that repeatedly brownouts, resets, or reports `fault_safe` with no
  cable connected must be powered down and diagnosed, not re-scanned.

## Self-test setup (first bring-up action after programming)

1. Connect only the **known-loopback adapter** (both ends on the carrier).
2. Connect USB. Run `precheck`; a pass returns a 5-second single-use token.
3. Run `self_test` with `manifest_revision` matching the adapter. Expected:
   all 16 groups match, `pass: true`, state returns `idle_safe`.
4. Any other result is a first-article assembly/mux fault — stop and go to
   troubleshooting.

Until `hardware/selection/limits-rev-a.json` carries `validated: true`,
precheck fails closed by design; the self-test above is therefore only
executable after the characterization in
`docs/characterization-plan.md` completes.

## Troubleshooting flow

Start: board plugged into USB, no cable attached.

1. **No USB enumeration at all** → different cable (data, not charge-only),
   different host port; if still dead, check U1 castellations for bridges and
   3V3 at the module with a DMM. Fault: power path.
2. **`hello` gets no answer** → firmware not flashed (re-flash), or CDC
   descriptor issue (check host logs). Fault: firmware/USB.
3. **`precheck` fails with `limits_unavailable`** → expected: the limits
   record is not yet validated. Do not work around it; that gate is the
   safety boundary. (Post-validation builds only:) precheck failure with
   voltage reasons on an **empty** bank indicates a front-end assembly fault:
   re-inspect D1–D40 orientation, mux solder, and the 10 kΩ/100 kΩ networks
   for the offending endpoint.
4. **`fault_safe` latched unexpectedly** → cause is in the fault reason;
   remove the cause, power-cycle if the reason is not recoverable, then run a
   new precheck. Never scan to "see if it recovered."
5. **Self-test reports opens** → reseat the loopback adapter; if the same
   position still opens, DMM-verify the adapter lead, then probe the
   corresponding mux output at its series resistor (board-only measurement).
6. **Self-test reports shorts/crossovers on known-good loops** → suspect mux
   solder bridges or a reversed adapter; run the DMM continuity check on the
   adapter, then inspect the associated U2–U9 pins.
7. **Intermittent self-test results** → reseat everything; inspect crimps and
   castellations; a flapping self-test must never be treated as a pass.
8. **Anything else** → document the raw frames and stop; do not improvise
   repairs beyond rework of the identified joint.

## Before first use with a real cable

- Self-test passed on the same day (post-limits-validation).
- The cable or harness is disconnected from **everything** — no power, no
  devices, no PoE, no batteries, no vehicle wiring.
- Both ends reach the correct bank/positions per the selected adapter's
  numbering.
- The companion app shows a passing precheck and the scan begins within the
  5-second token window.
