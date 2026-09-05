# Project-local footprints

`RaspberryPi_Pico_SMD_HandSolder.kicad_mod` is pinned from the official KiCad footprint library at commit `2b941bf1d97862be429793b46fd52a5add09a2fc` (the content used by the KiCad 9.0.9 tag):

<https://gitlab.com/kicad/libraries/kicad-footprints/-/blob/2b941bf1d97862be429793b46fd52a5add09a2fc/Module.pretty/RaspberryPi_Pico_SMD_HandSolder.kicad_mod>

The upstream library is licensed under Creative Commons CC-BY-SA 4.0 with the KiCad libraries exception; see <https://www.kicad.org/libraries/license/>. This attribution applies to the copied footprint, not to unrelated PinPath source files.

The footprint is kept project-local because the installed KiCad 9 footprint set does not contain it. Its edge pads 1–40 and SWD pads D1–D3 are cross-checked in `hardware/schematic-pinout-evidence.md`. PCB placement, courtyard/keepout use, and physical assembly remain issue #4 work.
