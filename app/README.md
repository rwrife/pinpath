# PinPath companion app

Local desktop companion for the PinPath de-energized cable/harness tester.

## Safety boundary (hard requirement)

PinPath is for **disconnected, de-energized passive assemblies only**. The app must not be used for or interpreted as support for mains, PoE, batteries/battery packs, powered USB test banks, automotive harnesses connected to vehicle power, medical/life-safety wiring, energized-circuit probing, or certification testing.

If precheck fails, scan faults, reset events, malformed frames, or user cancellation occur, the workflow returns to safe idle and requires a fresh precheck token before another scan.

## Stack and pinned tooling

- TypeScript `5.6.3`
- React `18.3.1`
- Vite `5.4.8`
- Vitest `2.1.1`
- ESLint `9.10.0`
- Tauri `2.0.1` (`@tauri-apps/cli` + Rust crate)
- Rust `1.98.0`
- SQLite via `rusqlite` with bundled SQLite

## Features implemented

- User-initiated USB discovery/connection (mock adapter first) with strict protocol/hardware compatibility gate.
- Precheck token workflow: scan is rejected unless precheck was run immediately beforehand.
- Unknown mapping and expected-profile comparison.
- Deterministic classification into match/open/short/crossover/unstable/unknown.
- Accessible, non-color-only 16×16 matrix rendering (`✓ O S X ! ?` text indicators plus color).
- Local profile/report persistence with SQLite migrations in Tauri runtime.
- Deletion controls for profiles/reports.
- Versioned JSON backup/restore and CSV report export.
- Serial frame validation with strict schema/limits, duplicate-key rejection, bounded sizes/depth, and sanitized user-visible/exported text.
- No account, telemetry, background network service, ad SDK, or cloud dependency.

## Commands (reproducible)

From `app/`:

```bash
npm ci
npm run lint
npm run test:ci
npm run a11y
npm run build
npm run tauri:build
```

## CI

`/.github/workflows/app.yml` runs:

1. `npm ci`
2. `npm run lint`
3. `npm run test:ci`
4. `npm run a11y`
5. `npm run build`
6. unsigned Tauri debug package build

## USB permissions by OS (development baseline)

- **Linux:** add udev rule for the adapter VID/PID and replug the device.
- **macOS:** no custom driver expected for CDC, but app needs user-granted USB/serial access if prompted.
- **Windows:** ensure WinUSB/CDC driver is present; first plug may require elevation/admin policy depending on enterprise controls.

Detailed operational notes live in `docs/usb-permissions.md`.

## Unsigned development artifacts

Current package outputs are unsigned development artifacts only. Signing/notarization remains a later milestone and is not claimed in this repository state.
