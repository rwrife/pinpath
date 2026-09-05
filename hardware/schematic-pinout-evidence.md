# Rev-A schematic pin, polarity, and footprint evidence

Status: **manufacturer-document-backed static cross-check; no physical or bench evidence**

Schematic: `hardware/pinpath.kicad_sch`

Hardware revision: `rev-a-candidate`

Review date: 2026-09-02

PinPath remains limited to disconnected, de-energized passive assemblies at a supervised dry indoor bench. Protection and precheck do not authorize testing energized wiring. Never connect mains, PoE, batteries or battery packs, powered USB through a test bank, vehicles, medical/life-safety wiring, or any energized circuit.

## Verification basis

The checked-in custom symbol library is `hardware/pinpath.kicad_sym`; each symbol is embedded in the schematic as well. Manufacturer-document URLs and the exact facts previously extracted from them remain in `hardware/selection/evidence-sources.json`. The checks below compare those pin tables/drawings with the final schematic symbols and assigned footprint pad numbers. KiCad library geometry is used only after the manufacturer package/pad order is established; it is not treated as the pinout authority.

## IC and module pin audit

| References | Manufacturer evidence | Final schematic pin mapping | Footprint/pad disposition |
|---|---|---|---|
| U1, Raspberry Pi Pico SC0915 | Raspberry Pi Pico Datasheet, Figure 2 pinout, Figure 4 physical numbering, §4.2 GPIO, §4.3 ADC, §4.4 Powerchain, Appendix B schematic: <https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf> | Edge pads 1–40 match the Pico physical numbering. Used controls: 1 GP0=`MUX_A0`, 2 GP1=`MUX_A1`, 4 GP2=`MUX_A2`, 5–7 GP3–5 drive enables, 9 GP6 fourth drive enable, 10–11 GP7–8 sense enables, 12 GP9=`STIM`, 14 GP10=`BIAS`, 15 GP11=`START_CANCEL_N`, 16–17 GP12–13 status, 31/32/34 ADC0/1/2 sense/reference. Grounds are 3/8/13/18/23/28/33/38. 36 is `+3V3`, 40 is `VBUS`, 30 is `RUN`. Debug pads are D1 SWCLK, D2 GND, D3 SWDIO, matching the selected footprint names. Unused GP14–22, ADC_VREF, 3V3_EN, and VSYS carry explicit no-connect markers. | Project-local `PinPath:RaspberryPi_Pico_SMD_HandSolder`, pinned from the KiCad 9.0.9 library commit `2b941bf1d97862be429793b46fd52a5add09a2fc`. It has edge pads 1–40 plus debug pads D1–D3 and cites the Pico manufacturer datasheet. This replaces the unavailable older `RaspberryPi_Pico_SMD_TH` hint while preserving no-header surface mounting and explicit SWD access. |
| U2–U9, TMUX1108PWR | TI TMUX1108 Rev. B, Table 5-1 Pin Functions: <https://www.ti.com/lit/ds/symlink/tmux1108.pdf> | TSSOP: 1 A0, 2 EN active-high, 3 VSS, 4 S1, 5 S2, 6 S3, 7 S4, 8 D, 9 S8, 10 S7, 11 S6, 12 S5, 13 VDD, 14 GND, 15 A2, 16 A1. U2/U3 drive A low/high, U4/U5 drive B low/high, U6/U7 sense A low/high, U8/U9 sense B low/high. VSS and GND go to GND for single-supply use. Every VDD has C1–C8; every active-high enable has an external 100 kΩ pulldown. | `Package_SO:TSSOP-16_4.4x5mm_P0.65mm`; pad count/order agrees with the TI PW package table. |
| U10, REF3318AIDBZR | TI REF33 Rev. I, Figure 5-1 and Table 5-1 Pin Functions: <https://www.ti.com/lit/ds/symlink/ref33.pdf> | DBZ SOT-23-3: pin 1 IN=`+3V3`, pin 2 OUT=`ADC_REF_1V8`, pin 3 GND. C9 bypasses IN, C10 loads OUT, and R75 feeds `BIAS`. | `Package_TO_SOT_SMD:SOT-23`; numeric pads 1–3 match the DBZ table. |

## Protection and polarity audit

| References | Manufacturer evidence | Final schematic mapping/polarity | Footprint disposition |
|---|---|---|---|
| D1–D32, BAS70-04,215 | Nexperia BAS70-04, Table 2 Pinning and internal connection diagram: <https://assets.nexperia.com/documents/data-sheet/BAS70-04.pdf> | Exact dual-series topology: pin 1 lower-diode anode to GND, pin 3 shared cathode/anode to the protected endpoint node, pin 2 upper-diode cathode to `+3V3`. `BAS70-05` and `BAS70-06` are prohibited substitutions because their common-cathode/common-anode topology is wrong. | `Package_TO_SOT_SMD:SOT-23`, numeric pads 1–3. |
| D33–D40, TPD4E1U06DCKR | TI TPD4E1U06 Rev. D, §5 Pin Configuration and Functions: <https://www.ti.com/lit/ds/symlink/tpd4e1u06.pdf> | SC70-6: 1 D1+, 6 D1−, 3 D2+, 4 D2− are four independent protected I/O channels; 2 is GND; 5 is NC and has an explicit no-connect marker. One device serves four protected internal nodes after the 10 kΩ connector-entry resistors. | `Package_TO_SOT_SMD:SOT-363_SC-70-6`, pads 1–6. PCB issue #4 must keep pin 2's ground return short and direct. |
| D41 READY, D42 FAULT | Kingbright APT2012LZGCK and APTD2012LSURCK datasheets: URLs in `hardware/selection/evidence-sources.json` | KiCad LED convention is pin 1 cathode and pin 2 anode. Pin 1 is GND; pin 2 receives GPIO-high drive through R77/R78. READY and FAULT remain separate LEDs with distinct text/icon cues; color is supplemental. | `LED_SMD:LED_0805_2012Metric`, pads 1 K / 2 A. Physical cathode-mark inspection remains an assembly gate. |
| C1–C10 | Murata exact product records in `hardware/selection/evidence-sources.json` | Non-polarized X7R MLCCs; no polarity requirement. C1–C8 are TMUX local bypass, C9 REF3318 input bypass, C10 REF3318 output/bias reservoir. | `Capacitor_SMD:C_0805_2012Metric`. |
| R1–R78 | Vishay D/CRCW e3 datasheet and part-number construction in `hardware/selection/evidence-sources.json` | Non-polarized. R1–R32 are the one-per-endpoint 10 kΩ entry limits; R33–R64 are endpoint-to-BIAS; R65–R74 are safe-default/control pulldowns; R75 is reference-to-BIAS; R76 is button pullup; R77/R78 limit LED current. | `Resistor_SMD:R_0805_2012Metric`. |

## Connector, control, and test-point audit

| References | Evidence and final mapping | Footprint disposition / open physical gate |
|---|---|---|
| J1 Bank A, J2 Bank B | Molex 43045-1600 official product record and sales drawing `430451600_sd.pdf`: <https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/430/43045/430451600_sd.pdf?inline>. Numeric pins 1–16 map directly to canonical `A:01`–`A:16` and `B:01`–`B:16`; no vendor number is exposed through firmware/UI naming. | `Connector_Molex:Molex_Micro-Fit_3.0_43045-1600_2x08_P3.00mm_Horizontal`. The KiCad 9 footprint has pads 1–16 plus two unnumbered mechanical board-lock pads. Issue #4 must place the key/pin-1 landmark and mating-face viewing direction on silkscreen/drawings. |
| J3 local SWD | Samtec configured-product record for FTSH-105-01-L-DV-K: <https://www.samtec.com/products/ftsh-105-01-l-dv-k>. Electrical assignment follows the Cortex 10-pin debug convention: 1 VTREF=`+3V3` sense, 2 SWDIO, 3/5/9 GND, 4 SWCLK, 10 nRESET/RUN; 6/7/8 are explicit NC. Debugger power is not accepted and no bank-power path exists. | `Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD` verifies the 2×5, 1.27 mm numeric pad grid. The exact key/shroud body and mating cable remain explicit issue #4 mechanical gates; this is not silently treated as final enclosure geometry. |
| SW1 | C&K/Littelfuse PTS636SK25FSMTRLFS product record and indexed 2025 PTS636 datasheet: <https://www.ckswitches.com/products/switches/product-details/Tactile/PTS636/PTS636SK25FSMTRLFS>. The switch is SPST-NO and non-polarized; it connects `START_CANCEL_N` to GND. | `Button_Switch_SMD:SW_Tactile_SPST_NO_Straight_CK_PTS636Sx25SMTRLFS`. Direct automated PDF retrieval still returns HTTP 403; the exact KiCad footprint name and manufacturer dimensions were checked against the indexed manufacturer record, but the latest PDF remains a disclosed document-availability gap rather than a fabricated local citation. |
| TP1–TP12 | Keystone 5015 official product/drawing record: <https://www.keyelco.com/product.cfm/product_id/1353>. Each part is one non-polarized electrical node. | `TestPoint:TestPoint_Keystone_5015_Micro-Minature`; required nets are VBUS, +3V3, GND, ADC_REF_1V8, BIAS, STIM, DRV_A_LO_EN, READY_LED, FAULT_LED, A:01_NODE, B:01_NODE, and RUN. |

## Net and safe-default conclusions

- USB VBUS and +3V3 appear only at U1 and named bring-up/control loads; neither rail connects directly to any `A:xx` or `B:xx` bank pin. The Pico module owns its Micro-USB connector, shield, ESD/power entry, and local bypassing; there is no separate carrier USB receptacle or carrier shield net to wire.
- Every external bank pin reaches its internal node only through exactly one 10 kΩ R1–R32 entry resistor.
- Every internal node has one 100 kΩ BIAS path, one exact BAS70-04 rail clamp, one TPD4E1U06 channel, and both its intended drive and sense mux channels.
- U2–U9 EN is active high. R65–R70 make all drive/sense paths disabled while Pico pins are unpowered, reset, booting, or high-impedance. R71–R74 give defined-low address/STIM defaults.
- `BIAS` connects REF3318 OUT through R75 and Pico GP10 directly. Firmware is still required to use GP10 only as output-low or input/high-impedance; hardware cannot prevent a software-driven high state.
- `hardware/selection/limits-rev-a.json` remains `validated: false` and `firmware_scan_authorized: false`. This schematic provides EDA evidence, not authorization to scan.

## Analyzer triage

The v1.4 schematic analyzer reported 156 components, 23 findings (0 errors, 3 warnings, 20 info), 100% MPN/Datasheet property coverage, and high provenance coverage. Its three warnings are narrow topology/classification false positives rather than waived electrical defects:

- `CG-AUD` on J1/J2: the bank connectors intentionally contain 16 isolated test endpoints and no shared ground pin. Adding ground would reduce usable endpoints and could create an unintended connection to the disconnected harness.
- `PU-001` on U1 `3V3_EN`: the Pico module pin is explicitly no-connected. The module provides the internal power-chain behavior described by the Pico datasheet; carrier control of `3V3_EN` is not required.
- ESD info says J1/J2 have no coverage because the analyzer does not trace the selected protection through the per-endpoint 10 kΩ entry resistors and label-based node fanout. The final netlist shows D33–D40 across all 32 internal endpoint nodes. J3 is a local supervised debug header, not a field connector.

Other relevant info findings are intentional: VBUS bypass/protection is on the Pico module, R75/C10 form the bias/reference low-pass, and lifecycle audit was not run because this change makes no order/lifecycle claim.

## Evidence limits

No PCB placement/routing, DRC, fabrication output, assembled fixture, hardware-in-loop run, bench measurement, ESD test, or field observation exists here. The native ERC result proves rule consistency, not physical correctness. Final connector keying, mechanical body clearances, ESD return layout, decoupling placement, thermal/current geometry, and all measured thresholds remain issues #4 and #7.
