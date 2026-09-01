# Hardware plan

## System block description

```text
USB 5 V SELV
    |
[power/protection] -> [RP2040 module + USB CDC]
                            |
                  [protected scan front end]
                     /                \
             [16-pin Bank A]      [16-pin Bank B]
                     |                  |
              passive adapter     passive adapter
                       \              /
                    de-energized cable
```

The rev-A schematic candidate uses Raspberry Pi Pico `SC0915`, eight TI `TMUX1108PWR` muxes for independent stimulus/sense paths, 10 kΩ endpoint current limiting, low-leakage rail clamps, four-channel ESD arrays, and a two-phase 0/1.8 V precheck bias. Exact references, packages, manufacturer properties, and GPIO allocation are in [the component-selection handoff](selection/component-selection.md). This selection and its DC model are static evidence only: `selection/limits-rev-a.json` remains `validated: false`, so no scan is authorized before later schematic/layout review and bench characterization. Normative behavior and evidence gates remain in [requirements](requirements.md), [architecture](../docs/architecture.md), [risk analysis](../docs/risk-analysis.md), and the [verification matrix](../docs/verification-matrix.md).

## Interfaces

- USB CDC for power, configuration, and reports
- Two keyed 16-position low-voltage test-bank connectors
- Replaceable passive adapters; first targets are numbered headers and labeled flying leads
- SWD or vendor-supported debug connection and a documented recovery path
- Physical start/cancel control and text/shape-capable or coded status indication

## Power plan

USB 5 V SELV enters only through the Pico micro-USB connector; its on-module supply generates 3V3 for the candidate front end. The two-phase precheck requires all 32 endpoints to track both a low bias and the measured 1.8 V reference while every stimulus enable is low. Provisional thresholds and calculated fault currents are recorded in `selection/limits-rev-a.json`, but are explicitly unvalidated and cannot authorize firmware scanning. The design must not source meaningful operating power into the item under test.

## Enclosure and assembly concept

A small screw-fastened or snap-fit printed enclosure will expose the two adapter sockets, USB, button, and status window. The PCB will use hand-assembly-friendly parts where practical, mounting holes, clear pin numbering, probeable test points, and replaceable adapters so connector wear does not require replacing the main board.

## Safety limits

Use only with fully disconnected, de-energized passive cables and harnesses. Never attach mains, PoE, powered USB through a test bank, a battery or battery pack, vehicles, medical or life-safety wiring, or any energized circuit. PinPath makes no cable certification claim and is not a hipot tester, insulation tester, precision ohmmeter, or protective instrument. Protection circuitry cannot make prohibited live testing safe.

## Expected editable KiCad deliverables

The intended source paths are:

- `hardware/pinpath.kicad_pro`
- `hardware/pinpath.kicad_sch`
- `hardware/pinpath.kicad_pcb`
- `hardware/adapters/<adapter>.kicad_pro/.kicad_sch/.kicad_pcb`

These KiCad files **do not exist yet**. Issue #3 must create real editable sources, import the properties from `selection/parts-handoff.json`, and verify every pin/pad against manufacturer documents; image-only diagrams are not substitutes. Future work must retain ERC/DRC reports and fabrication-output inspection evidence. Final Manufacturer/MPN data belongs in schematic symbol properties and exports to tracked `bom/bom.csv`.
