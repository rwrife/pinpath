# PinPath rev-A candidate component selection

Status: **selected for schematic capture; static analysis only; not electrically or physically validated**
Evidence date: **2026-09-01**

This document closes the pre-schematic selection work in issue #2. It does not authorize ordering, scanning, or energized testing. PinPath remains limited to disconnected, de-energized passive assemblies at a supervised indoor dry bench. Never connect mains, PoE, a battery or battery pack, powered USB through a test bank, vehicles, medical or life-safety wiring, or any energized circuit. The protection below reduces ordinary fault stress; it does not turn PinPath into a live-circuit probe, protective instrument, hipot/insulation tester, precision ohmmeter, or cable certifier.

Machine-readable artifacts:

- [`parts-handoff.json`](parts-handoff.json) — future references, values, packages, property values, connector/debug accessories, and GPIO allocation
- [`limits-rev-a.json`](limits-rev-a.json) — versioned provisional limits with `validated: false` and `firmware_scan_authorized: false`
- [`evidence-sources.json`](evidence-sources.json) — manufacturer documents, sections, and facts used
- [`availability-2026-09-01.csv`](availability-2026-09-01.csv) — dated, deliberately narrow public availability observations
- [`calculate_frontend.py`](calculate_frontend.py) and generated [`front-end-analysis.json`](front-end-analysis.json) — dependency-free DC nodal calculation

Downloaded PDFs were reviewed locally under ignored `datasheets/`. Durable manufacturer URLs are retained in `evidence-sources.json`; large PDFs are intentionally not committed.

## Selection constraints

The frozen requirements drive these constraints:

1. Exactly 32 canonical endpoints (`A:01`–`A:16`, `B:01`–`B:16`) must each support precheck, stimulus, sensing, and reporting.
2. Hardware and reset defaults must disable every stimulus path. Firmware may enable at most one endpoint after a fresh all-endpoint precheck.
3. Precheck must detect a fixed unexpected source of either polarity and must detect reference/bias faults; treating negative voltage as zero is unacceptable.
4. Every exposed endpoint needs a bounded DC path, low-leakage measurement path, and ordinary bench ESD treatment.
5. Default eight-repetition and maximum 64-repetition scans must fit the 30 s protocol bound.
6. USB micro-B on the selected controller module is the only normal power/data input. No radio, battery, external bank power, or host raw-GPIO interface is allowed.
7. The board remains hand-assembly/rework conscious: 0805 passives, TSSOP/SOT/SC70 packages, through-hole bank connectors, and a castellated controller module are preferred over BGAs or leadless protection arrays.
8. Every critical part needs an exact Manufacturer/MPN, package, source, and manufacturer document before schematic capture.

## Selected architecture

### Controller and USB/power

**Selected: Raspberry Pi Pico `SC0915`.** Its manufacturer datasheet documents 26 exposed 3.3 V GPIO, including GPIO26–28 ADC inputs, a micro-USB B power/data connector, USB series resistors, on-module flash/regulation, and a 3-pin SWD interface. The planned allocation uses 17 exposed GPIO, leaving GP14–GP22 spare. The carrier takes normal power only from the Pico micro-USB connector and consumes the module's 3V3 output; it adds no battery or secondary power input.

The Pico datasheet recommends keeping external 3V3 load below 300 mA. Eight muxes, reference, LEDs, and passive networks are far below that ceiling by component quiescent-current data, but issue #3 must produce a rail budget and issue #7 must measure supply current. RP2040 ADC-capable pins have a protection diode to IOVDD and must remain below approximately IOVDD + 300 mV; the external series/clamp network is therefore mandatory. Applying external voltage while the module is unpowered can back-power IOVDD and remains prohibited.

Alternatives reviewed:

- **Pico H:** electrically similar but preinstalled headers complicate low-profile carrier assembly; rejected.
- **Pico W:** adds an unused radio and its layout/antenna constraints conflict with the local/offline minimum; rejected.
- **Bare RP2040:** could reduce recurring cost but adds USB, flash, oscillator, regulator, boot, and fine-pitch/QFN layout risk before the front end is proven; deferred beyond MVP.

### Independent stimulus and sense routing

**Selected: eight TI `TMUX1108PWR` 8:1 precision muxes.** Four muxes independently select one of four endpoint octets for stimulus; four select the same octets for sensing. Their address lines are shared. Stimulus drain pins share `STIM`; only one of four active-high stimulus enables may be asserted. Each bank's two sense drain pins share one ADC input because only the low or high octet is enabled at a time. Low/high sense enables are shared across Bank A and Bank B so both ADC channels can be sampled together.

TI specifies at 3.3 V and -40 °C to +125 °C: 9.75 Ω maximum on-resistance, 1.5 nA maximum off/on leakage, 1.35 V minimum logic-high, 0.8 V maximum logic-low, and 60 mA continuous switch current at 125 °C. `EN` is active high; external 100 kΩ pulldowns therefore disable all eight muxes while the Pico is unpowered, reset, booting, or high impedance. The device itself provides break-before-make switching, but firmware must still clear and verify all drive-enable shadow bits before changing address or stimulus.

Alternatives reviewed:

- **TI `CD74HC4067M96`, four 16:1 muxes:** cheaper/fewer devices, but its full-temperature off leakage reaches ±8 µA. Across a practical endpoint bias resistor this can become hundreds of millivolts and erode open/precheck margin. Rejected after quantitative review.
- **ADI `ADG706BRUZ`, four 16:1 muxes:** nA-class leakage and simple routing, but the public single-unit listing observed on 2026-09-01 was about USD 8.77 each, roughly USD 35 for muxes alone. Rejected against the whole-prototype cost target.
- **GPIO expanders/direct GPIO:** direct GPIO cannot provide 32 protected independent drive-and-sense nodes with the Pico's pin count; common digital expanders do not provide the required ADC precheck path. Rejected.

### Endpoint network and ESD

Each endpoint uses the same network:

```text
bank connector
    |
  10 kΩ 1% 0805  (CRCW080510K0FKEA)
    |
protected internal node ----- stimulus TMUX channel
    |                         sense TMUX channel
    +-- 100 kΩ 1% ---------- BIAS
    +-- BAS70-04 dual-series clamp --> GND / 3V3
    +-- one TPD4E1U06 channel ------> GND
```

**10 kΩ series resistor.** Vishay's current D/CRCW document rates the 0805 standard mode at 0.125 W and 150 V. It bounds stimulus, contention, clamp, and ADC injection paths before any semiconductor.

**Low-leak rail clamp: Nexperia `BAS70-04,215`.** The dual-series SOT-23 topology is critical: pin 3 is the protected node, pin 1 the lower/GND clamp anode, and pin 2 the upper/3V3 clamp cathode. Nexperia specifies 70 V reverse, 70 mA continuous, 410 mV maximum forward drop at 1 mA, and 100 nA maximum reverse leakage at 50 V and 25 °C. `BAT54S` was rejected because its 2 µA leakage limit at 25 V consumed too much of the precheck budget. Issue #3 must prohibit `BAS70-05/-06` substitutions because their common-cathode/common-anode topology is wrong.

**ESD: TI `TPD4E1U06DCKR`.** One SC70-6 device protects four internal endpoint nodes after their 10 kΩ resistors. TI specifies four channels, ±15 kV IEC 61000-4-2 contact and air, 0–5.5 V operating input, 10 nA maximum leakage, and 6.5 V minimum breakdown. Placement needs a short direct ground return. This is ordinary handling protection only; no immunity or live-input claim is made without PCB and pre-compliance evidence.

### Two-phase precheck and complementary continuity scan

**Reference: TI `REF3318AIDBZR`.** The 1.8 V SOT-23 reference has ±0.15% maximum initial accuracy, 30 ppm/°C maximum drift, and a ±5 mA output range. Its output goes to RP2040 ADC2 as `ADC_REF_1V8` and through 1 kΩ to common `BIAS`.

`BIAS_CTRL` is intentionally restricted to two electrical states:

- output-low: BIAS approximately 0 V; the reference sources 1.8 mA through the 1 kΩ feed;
- input/high-impedance: BIAS approximately the measured 1.8 V reference.

Firmware must never drive `BIAS_CTRL` high. With all stimulus enables low, precheck samples all endpoints once in each bias state. A floating, de-energized passive network follows both states. A fixed external source may match one phase but cannot follow both. A stuck-low bias, missing reference, saturated ADC, missing endpoint sample, or inconsistent repeat therefore fails closed. This explicitly fixes the negative-voltage blind spot of a simple ground-biased ADC precheck.

Continuity scans use both high-STIM/low-BIAS and low-STIM/1.8-V-BIAS phases. Comparing signed endpoint delta from the active bias rejects single-polarity/stuck observations and preserves a 32-node short response in the static model.

### Bank connectors

**Selected board header: Molex `43045-1600`; mating housing: `43025-1600`; provisional 20–24 AWG contact: `43030-0007`.** The Micro-Fit 3.0 pair is polarized, latching, dual-row, 16-circuit, and mechanically more appropriate for replaceable adapters than an unkeyed 0.1-inch header. The 43045 right-angle board header puts connector load at the enclosure edge. PinPath current is orders of magnitude below the connector family rating.

The contact remains `SELECTED_WITH_STOCK_GAP`: Molex documentation identifies the exact contact and wire range, but no authorized partner stock quantity was captured. Wire gauge, approved crimp tooling, and authorized availability must be confirmed before ordering. Adapter drawings must state mating-face orientation and map every Molex cavity to a canonical endpoint; no vendor pin-order assumption may cross into protocol/UI naming.

Alternatives reviewed:

- **Unshrouded 2.54 mm headers/IDC:** inexpensive but reversal and ambiguous mating-face numbering are credible; rejected for the main replaceable bank interface.
- **JST-style single-row families:** would create a long edge and less robust 16-position service interface; rejected.
- **Higher-current power connectors:** unnecessary bulk/cost for sub-mA stimulus; rejected.

### Controls, indication, debug, and testability

- **Start/cancel:** C&K `PTS636SK25FSMTRLFS`, SPST-NO top-actuated SMT. It is a deliberate local input only; connection never starts a scan. The manufacturer PDF URL is retained, but automated retrieval returned HTTP 403. Latest-PDF manual inspection is a narrow open gate before issue #3 freezes the footprint.
- **Status:** separate Kingbright `APT2012LZGCK` green READY and `APTD2012LSURCK` red FAULT 0805 LEDs. Separate durable `READY`/`FAULT` text and distinct icons/timing are mandatory; color is supplemental. One RGB LED was rejected because a single shared non-color cue makes ready/fault ambiguity more likely.
- **Debug:** Samtec `FTSH-105-01-L-DV-K` keyed 10-pin 1.27 mm SWD header. VTREF is sense-only; debugger power is not accepted. Debug remains controller-only with no bank power path. Raspberry Pi `SC0889` is a non-schematic candidate debug probe; a matching adapter cable still needs selection.
- **Test points:** Keystone `5015` SMT loops are allocated to VBUS, 3V3, GND, ADC reference, BIAS, STIM, drive enable/control, READY, FAULT, A:01 internal, B:01 internal, and RUN/reset.

## Static calculations and margins

Run:

```bash
python3 hardware/selection/calculate_frontend.py \
  --output hardware/selection/front-end-analysis.json
python3 -m unittest discover -s hardware/selection -p 'test_*.py' -v
```

The model is a linear DC nodal solve with ideal cable connections. It is **not SPICE** and includes no contact resistance, cable capacitance, ADC quantization/noise, PCB parasitics, transient ESD behavior, or physical component variation beyond the listed resistor/mux limits.

Using 3.0 V minimum stimulus, 10.1 kΩ maximum series resistors, 99 kΩ minimum bias resistors, and 9.75 Ω maximum mux on-resistance:

| Check | Calculated result | Selected-part comparison |
|---|---:|---|
| 32-node group, high stimulus/low bias | +0.703 V remote delta | provisional detect threshold 0.25 V |
| 32-node group, low stimulus/1.8 V bias | -0.422 V remote delta | provisional detect threshold 0.25 V |
| Open-node leakage error budget | 11.3 mV | below 0.20 V provisional precheck guard |
| Fixed external-source sweep | -5, -1, 0, 1.8, 3.3, +5 V; 0 and 10 kΩ source resistance | every case fails at least one 0/1.8 V bias phase |
| Driven endpoint shorted to ground | 0.367 mA | below TMUX 60 mA at 125 °C |
| Two opposing drive paths shorted | 0.183 mA | below TMUX 60 mA and BAS70 70 mA |
| Single +5 V external fault while USB-powered | 0.097 mA clamp, 0.093 mW resistor | below continuous ratings |
| Single -5 V external fault while USB-powered | 0.464 mA clamp, 2.13 mW resistor | below continuous ratings |
| 64 reps, 32 drives × 2 polarities × 32 readings at 120 µs | 15.73 s conversion budget | leaves 14.27 s under 30 s for state/protocol overhead |
| Default 8 reps conversion budget | 1.97 s | bounded start point; bench timing pending |

The ±5 V calculation is a **single-endpoint bounded accidental stress case while USB-powered**, not an input rating. It does not cover simultaneous multi-endpoint drive, unpowered backfeed, high-energy sources, or transients. All energized connection remains prohibited.

The lowest continuous semiconductor rating used in the checked path is 60 mA (TMUX at 125 °C), over 100 times the largest calculated DC fault current. The 0805 resistor's largest calculated DC fault dissipation is under 2% of its 0.125 W standard-mode rating. These are static arithmetic margins, not proof that the assembled board survives misuse.

## Provisional limits and required safe state

`limits-rev-a.json` deliberately contains:

```json
"validated": false,
"firmware_scan_authorized": false
```

Issue #5 firmware must refuse precheck authorization/self-test/scan if that remains false, the record is absent, malformed, or revision-incompatible. Failed precheck, reset, brownout, cancel, disconnect, watchdog, malformed input, and internal invariant failure all require:

1. all four stimulus enables low;
2. STIM low/input-safe;
3. BIAS_CTRL input/high-impedance unless actively executing a bounded precheck/scan phase;
4. mux/address/control GPIO returned to input/high-impedance with internal pulls disabled after external pulldowns have taken effect;
5. result partial/non-passing with a stable reason code;
6. a new precheck before any later stimulus.

No host command may expose raw GPIO, hold stimulus indefinitely, skip precheck, change electrical limits, or override a fault.

## Availability, lifecycle, and cost disposition

`availability-2026-09-01.csv` records only what was actually observed. Manufacturer product pages/datasheets were current for the selected silicon and major connectors, and public DigiKey pages existed for most exact MPNs. The TMUX listing also had a public LCSC search record showing a price from about USD 1.70–1.78. Exact authorized stock quantities, complete single-unit pricing, shipping, tax, PCB/enclosure cost, and several passive/contact quantities were not captured because DigiKey API credentials were unavailable and public snippets are not an orderable quote.

Therefore the USD 35–60 target and USD 75 ceiling remain **unknown**, not “met.” Before an order, rerun authorized distributor API searches for every exact MPN, record quantity-one and build-quantity prices, confirm the Molex contact/tooling/cable, add PCB/enclosure/fasteners, and roll up dated totals. Never reuse the 2026-09-01 snippets as current stock proof.

## Footprint and evidence gaps handed to later issues

1. **KiCad library unavailable on this runner.** The KiCad MCP footprint search returned `Footprint library path not found: None`, and `kicad-cli` was absent. `parts-handoff.json` gives package-backed footprint hints only. Issue #3 must inspect or create each land pattern and verify every pin/pad against manufacturer drawings.
2. **C&K PDF retrieval blocked.** Manually inspect the latest switch PDF and land pattern before schematic freeze.
3. **No SPICE simulator installed.** `ngspice`, `ltspice`, and `xyce` were absent. The committed solver is static DC only. Use SPICE later for ADC settling, parasitic capacitance, switch charge injection, and transient fault behavior when tooling is available.
4. **No physical evidence.** No schematic, PCB, fabricated unit, HIL setup, bench measurement, ESD test, or field observation exists from this issue.
5. **System temperature unvalidated.** Individual parts have manufacturer ranges, but the active limits record has no validated operating temperature until issue #7.
6. **Ordering gaps remain.** Exact stock/pricing and debug cable are open; the BOM marks these rather than inventing data.

## Issue #3 schematic capture checklist

- Import all Manufacturer, MPN, Datasheet, supplier/source, and BOM comments from `parts-handoff.json` into symbol properties.
- Verify U1 module pin names, U2–U9 TSSOP pin numbers, U10 SOT-23 pinout, D1–D32 dual-series clamp polarity, D33–D40 SC70 channels, both LED polarities, connector cavities/pad numbers, and SWD pinout directly from manufacturer documents.
- Keep `DRV_*_EN` active-high with external pulldowns; do not rely on firmware/internal pulls.
- Make BIAS_CTRL low/high-Z only and show the 1 kΩ reference feed explicitly.
- Run native ERC plus schematic analyzers; document only narrow intentional exceptions.
- Export `bom/bom.csv` from schematic properties. This preliminary BOM remains a selection handoff, not an order file.
