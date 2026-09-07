# PinPath firmware (issue #5 baseline)

This directory now contains a reproducible Pico SDK/CMake firmware scaffold plus host-testable core logic for safe-state sequencing, precheck/token gates, bounded scan scheduling, and protocol enforcement.

## Safety boundary (normative)

PinPath firmware only applies to disconnected, de-energized passive assemblies. It does **not** authorize mains, PoE, battery or battery pack use, powered USB through a test bank, vehicles, medical/life-safety wiring, energized circuits, or cable certification claims.

The firmware fails closed:

- startup enters safe high-impedance behavior,
- precheck is required before scan/self-test,
- precheck token is single-use and expires after 5 seconds,
- malformed/invalid state-changing commands invalidate the armed token,
- unexpected voltage latches fault-safe,
- scan completion/cancel/fault returns to safe condition.

## What was implemented

- `src/pinpath_core.*`:
  - protocol frame bounds (`<= 32768` bytes, max depth 8, duplicate top-level key rejection),
  - envelope validation (`v/type/id/payload`), ID replay rejection,
  - state machine (`idle_safe`, `armed`, `scanning`, `classifying`, `fault_safe`),
  - precheck gate + token expiry/consumption,
  - one-drive-at-a-time bounded scheduler,
  - unknown-map + expected-map result shaping,
  - classifier buckets (`matched`, `open`, `short`, `crossover`, `unstable`, `not_evaluated`),
  - bounded progress messages.
- `src/main.cpp`: RP2040 USB-CDC newline JSON loop wiring the protocol engine into a HAL/clock abstraction.
- `tests/test_core.cpp`: host unit/property-style tests for malformed, oversized, duplicate-id, duplicate-key, out-of-order/invalid-state, token expiry, crossover classification, and safe-state/token invalidation behavior.
- `hil/run_fixture.py`: serial HIL fixture runner that records `device_observation` by default and only emits `bench` context when a complete bench metadata record is supplied.

## Pinned SDK/toolchain

Pinned Pico SDK submodule:

- path: `third_party/pico-sdk`
- tag/commit: `2.0.0` / `efe2103f9b28458a1615ff096054479743ade236`

### Clone/update with submodules

```bash
git submodule update --init --recursive
```

## Reproducible build commands

### Host tests (runs on any dev host with CMake + C++17 compiler)

```bash
cmake -S firmware -B firmware/build-host -DPINPATH_BUILD_FIRMWARE=OFF -DPINPATH_BUILD_TESTS=ON
cmake --build firmware/build-host -j
ctest --test-dir firmware/build-host --output-on-failure
```

### RP2040 firmware build (requires `arm-none-eabi-gcc` toolchain)

```bash
cmake -S firmware -B firmware/build-pico -DPINPATH_BUILD_FIRMWARE=ON -DPINPATH_BUILD_TESTS=OFF
cmake --build firmware/build-pico -j --target pinpath_firmware
```

Outputs include `pinpath_firmware.uf2` via `pico_add_extra_outputs`.

## Flash, debug, and recovery

### Flash (UF2)

1. Hold BOOTSEL while plugging in Pico USB.
2. Mounts as mass-storage boot volume.
3. Copy `firmware/build-pico/pinpath_firmware.uf2` to that volume.
4. Device reboots into firmware.

### Debug

- Use SWD (`FTSH-105-01-L-DV-K` footprint on hardware schematic).
- Debug is controller-only and must never source test-bank stimulus.

### Recovery

- Any fault/reset/disconnect path must return to safe condition.
- If protocol rejects state-changing input while armed, the token is invalidated and precheck must be repeated.

## HIL fixture usage (not yet executed here)

```bash
python3 firmware/hil/run_fixture.py \
  --port /dev/ttyACM0 \
  --output firmware/hil/out/transcript.json
```

To mark evidence context as `bench`, provide filled metadata:

```bash
python3 firmware/hil/run_fixture.py \
  --port /dev/ttyACM0 \
  --bench-record firmware/hil/bench-record-template.json \
  --output firmware/hil/out/transcript.json
```

Without real fabricated hardware and measured setup records, any transcript remains non-validation device observation.
