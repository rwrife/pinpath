# Third-party notices

PinPath source is MIT-licensed (see `LICENSE`). It incorporates or depends on
third-party material with its own licenses, listed here for attribution.
Versions are the ones pinned or recorded in this repository as of 2026-09-19.

## Vendored / submodule code

| Component | Version / pin | License | Location | Copyright |
|---|---|---|---|---|
| Raspberry Pi Pico SDK (git submodule) | tag 2.0.0, commit `efe2103f9b28458a1615ff096054479743ade236` | BSD-3-Clause (plus bundled components under their own licenses; see the SDK's own `LICENSE.TXT` inside the submodule) | `third_party/pico-sdk` | Raspberry Pi (Trading) Ltd. |
| nlohmann/json (single header) | bundled copy, 3.x (see file header) | MIT | `firmware/third_party/nlohmann/json.hpp`, license at `firmware/third_party/nlohmann/LICENSE.MIT` | Copyright (c) 2013-2022 Niels Lohmann |

## Build/host dependencies (not vendored; pinned in lockfiles)

| Component | Pinned version | License | Where declared |
|---|---|---|---|
| arm-none-eabi-gcc toolchain | CI-provided (`ubuntu24.04` package set, see `.github/workflows/firmware.yml`) | GPL-2.0+ / GCC Runtime Library Exception (does not affect PinPath code) | firmware CI |
| Node.js / npm packages (React, Vite, Vitest, ESLint, Tauri npm crates) | see `app/package-lock.json` | MIT/Apache-2.0 and per-package (lockfile records each) | `app/` |
| Rust crates (Tauri 2, rusqlite with bundled SQLite) | see `app/src-tauri/Cargo.lock` | MIT/Apache-2.0/MIT per crate; SQLite is public domain | `app/src-tauri/` |

## Hardware documentation references

Manufacturer datasheets referenced by `hardware/selection/evidence-sources.json`
(SC0915, TMUX1108PWR, REF3318AIDBZR, TPD4E1U06DCKR, BAS70-04, Molex/Samtec
connector documents) remain © their respective manufacturers; only selected
pinout/limit facts are cited, and the large PDFs are intentionally not
committed to this repository.

## KiCad libraries

Project-local symbols/footprints under `hardware/pinpath.pretty/`,
`hardware/TestPoint.pretty/`, and `hardware/pinpath.kicad_sym` are original
work of this project (MIT). Where KiCad standard libraries informed footprints,
those libraries are CC-BY-SA 4.0; no unmodified standard-library file is
redistributed as this project's own.
