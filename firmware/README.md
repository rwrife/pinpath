# Firmware plan

## Responsibilities

- Start in a safe high-impedance state.
- Run external-voltage precheck before every fixture self-test or cable scan.
- Schedule one-node-at-a-time stimulus and bounded sampling.
- Classify observations into connected, open, shorted, crossed, unstable, or fault states without overstating certainty.
- Stream progress and final maps over a versioned USB CDC protocol.
- Support local start/cancel, visible fault state, watchdog recovery, and documented bootloader/reflash behavior.

## Safety boundary

Firmware operates only on disconnected, de-energized passive assemblies and cannot override a failed precheck. It does not authorize mains, PoE, battery or battery-pack, powered USB through a test bank, vehicle, medical, life-safety, energized-circuit, or cable certification use.

## Interfaces and protocol

The firmware will implement the device side of [`docs/protocol.md`](../docs/protocol.md) and the safe-state/classification contract in [`docs/architecture.md`](../docs/architecture.md). GPIO, ADC/comparator input, indicator, control, time source, and USB transport sit behind narrow interfaces so scan/classifier behavior can run in host tests without fabricated hardware. The [verification matrix](../docs/verification-matrix.md) defines which host tests are simulation evidence and which later checks require a real board.

## Provisioning and update

The planned baseline is a reproducible Pico SDK/CMake build and UF2 installation through the controller's ROM bootloader or documented module recovery mechanism. Firmware images must carry protocol and hardware-revision compatibility metadata. No network OTA updater is planned.

## Test strategy

- Host unit/property tests for scan scheduling, adjacency-map classification, retries, cancellation, and bounds
- Protocol parser tests with malformed, oversized, duplicated, and out-of-order frames
- Firmware compile and static checks in CI
- Hardware-in-loop loopback tests only after a real board exists
- Bench fault-injection tests for opens, shorts, crossovers, unstable contacts, and unexpected-voltage lockout

No firmware source, build result, flashing result, or physical test exists in this scaffold.
