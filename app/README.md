# Companion app plan

## Responsibilities

The local desktop companion will discover a user-selected PinPath serial device, guide safe setup, create expected cable profiles, render the observed 16×16 map, compare results, retain optional history, and export reports. It must keep unsafe operations unavailable after a device fault or failed precheck.

PinPath is only for disconnected, de-energized passive assemblies. The app shall not enable or imply mains, PoE, battery or battery-pack, powered USB through a test bank, vehicle, medical, life-safety, energized-circuit, or cable certification use.

## Target platforms and framework

Tauri 2 with a Rust service boundary and TypeScript UI, targeting Windows 10/11, macOS, and Linux. Platform serial adapters remain isolated behind a testable interface. Exact packaging and signing support will be validated per OS.

## Setup flow

1. Show the safety limits before first use and when hardware revision/limits change.
2. Ask the user to connect PinPath over USB; no background scanning before consent.
3. Verify protocol/hardware compatibility and offer fixture self-test.
4. Create/import an expected map or choose unknown-cable mapping.
5. Start/cancel the scan and review/export results.

## Data ownership and privacy

Profiles and reports are stored locally in SQLite. Versioned JSON supports complete backup/restore; CSV supports human-readable result export. The app has no account, telemetry, ads, cloud API, or required network permission. USB and filesystem access are requested only for explicit device or import/export actions. Users can delete individual reports or all local data.

## Accessibility

Keyboard-only operation, screen-reader names and announcements, scalable typography, non-color-only map states, high contrast, reduced motion, and clear focus order are MVP acceptance criteria.

## Protocol boundary

The app treats all serial input as untrusted and enforces schema, version, identifier, range, size, and state-transition checks. It never interprets device text as code or shell input. See the normative [`docs/protocol.md`](../docs/protocol.md), connectivity/report semantics in [`docs/architecture.md`](../docs/architecture.md), and evidence split in [`docs/verification-matrix.md`](../docs/verification-matrix.md).

No application skeleton, build, test, package, or live-device result exists yet.
