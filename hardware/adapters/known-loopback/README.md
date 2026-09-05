# Known-loopback adapter

This directory contains the editable electrical definition for the passive rev-A candidate self-test harness:

- `known-loopback.kicad_pro` / `known-loopback.kicad_sch` — two 16-position keyed mating housings wired one-to-one.
- `adapter-manifest.json` — canonical expected groups `A:01↔B:01` through `A:16↔B:16`.
- `known-loopback-erc.rpt` — native KiCad 9 ERC result.
- `known-loopback-schematic.pdf` — review export; it supplements, and does not replace, the editable source.

The design is a **static electrical definition only**. No harness has been built or continuity-tested. Connector mating-face orientation, cavity numbering, key landmarks, contact/wire choice, crimp tooling, mechanical retention, and assembled-fixture continuity remain issue #4/#7 gates.

Use only with disconnected, de-energized passive assemblies. This fixture does not authorize energized testing and must never be connected to mains, PoE, batteries or battery packs, powered USB through a test bank, vehicles, medical/life-safety wiring, or any energized circuit.
