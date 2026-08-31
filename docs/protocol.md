# PinPath device/app protocol baseline

Status: **normative MVP protocol semantics; implementation pending**. There is no firmware, app, or physical-device result yet.

The protocol applies only to disconnected, de-energized passive assemblies. It does not authorize mains, PoE, battery or battery-pack, powered USB through a test bank, vehicle, medical, life-safety, energized-circuit, or cable certification use.

## Transport and resource bounds

Transport is USB CDC with one newline-delimited UTF-8 JSON object per frame. The terminating LF is not part of the JSON value. Senders shall not rely on CRLF; receivers may accept and strip one CR before LF.

Receivers reject a frame before state change or unbounded allocation when any bound is exceeded:

- encoded frame: 32,768 bytes maximum, excluding line terminator;
- nesting depth: 8 maximum;
- any string: 256 Unicode scalar values maximum;
- undirected edge records: 496 maximum (every possible pair among 32 endpoints);
- endpoint/group records: 32 maximum;
- repetitions: integer 3–64, default 8;
- one outstanding state-changing request at a time.

Malformed UTF-8, duplicate JSON object keys, non-integer numeric fields where integers are required, unknown required fields, non-finite numbers, and trailing non-whitespace data are invalid. Additive optional fields may be ignored only within a recognized protocol major and message type.

## Common envelope

Every frame is an object:

```json
{"v":1,"type":"hello","id":"01J...","payload":{}}
```

- `v`: positive integer protocol major; MVP is `1`.
- `type`: closed message-type string for the receiving state.
- `id`: app-generated opaque non-empty string, at most 64 scalar values. Responses to a command echo it. Device-originated asynchronous messages use the active request id.
- `payload`: object with type-specific fields.

An unknown major is rejected without enabling stimulus. If any malformed, oversized, duplicate-id, incompatible, or otherwise rejected command/frame arrives while `armed`, the device invalidates the precheck token and returns to `idle_safe` or `fault_safe`; a new precheck is required. Reuse of an active or recently completed id in one connection session is rejected as `duplicate_id`.

## Canonical data types

### Endpoint

An endpoint is exactly `A:01`–`A:16` or `B:01`–`B:16`. It is case-sensitive and zero-padded. Raw MCU GPIO or connector pad numbers are not protocol values.

### Connectivity group

A group is a sorted array of unique endpoints. Groups in a collection are disjoint and lexically sorted by their first endpoint. Expected groups contain at least two endpoints; omitted expected endpoints mean expected-isolated. Observed groups include one-member groups so all 32 endpoints are represented.

### Edge observation

An undirected edge is encoded with lexically ordered `a < b`, `seen` count, and `opportunities` count. Duplicate/reversed edges are invalid. `seen=0` is stable disconnected, `seen=opportunities` is stable connected, and an intermediate count is unstable.

## Device states

Wire-visible states are:

- `boot_safe`
- `idle_safe`
- `prechecking`
- `armed`
- `self_testing`
- `scanning`
- `classifying`
- `fault_safe`

All states except active precheck/scheduled stimulus preserve the bank safe condition as defined in REQ-SAF-001. `armed` contains a single-use token, but no active drive.

## Command flow

```text
app -> hello
app <- hello_result
app -> precheck
app <- precheck_result {pass|fail}
app -> self_test | scan     # only armed with a compatible unexpired token
app <- progress*            # bounded, monotonic counters
app <- self_test_result | scan_result | cancelled | fault
app -> cancel               # accepted during precheck/self-test/scan/classify
```

Device connection never starts precheck or scan. After terminal response, the device is `idle_safe` or `fault_safe`, never left actively driving.

## Commands and responses

### `hello` / `hello_result`

`hello` has an empty payload. `hello_result` returns:

```json
{
  "hardware_revision":"string",
  "firmware_version":"string",
  "protocol_major":1,
  "limits_revision":"string",
  "limits_validated":false,
  "adapter_revision":"string-or-none",
  "capabilities":["precheck","self_test","unknown_map","expected_map"],
  "state":"idle_safe"
}
```

An absent/unvalidated limits record is visible and prevents `armed`/scan behavior.

### `precheck` / `precheck_result`

Accepted only from `idle_safe` or recoverable `fault_safe`, with no active stimulus. Payload declares the expected adapter revision or explicit `none`. The result contains all 32 endpoint observations, reference/self-diagnostic status, hardware/limits/adapter revisions, status `pass|fail`, and stable reason codes.

A pass enters `armed` and creates a device-internal token that expires after 5 seconds and is consumed by one `self_test` or `scan`. The token itself is not host-editable. A fail enters `fault_safe` or returns `idle_safe` according to the documented reason, always with no token.

### `self_test` / `self_test_result`

Accepted only from `armed` with a compatible known-loopback manifest. Payload supplies manifest revision and repetitions (default 8). The device validates declared loopback groups and expected-isolated endpoints. Any open, extra group, short, mismatch, or unstable relation fails self-test. Completion consumes the token and returns safe.

### `scan` / `scan_result`

Accepted only from `armed`. Payload:

- `mode`: `unknown_map` or `expected_map`;
- `repetitions`: 3–64, default 8;
- `expected_groups`: required only for `expected_map`, normalized and disjoint;
- `profile_schema`: required only for `expected_map`.

A complete `unknown_map` result reports all normalized observed groups and edge repetition evidence. A complete `expected_map` result additionally reports `matched`, `open`, `short`, `crossover`, `unstable`, and `not_evaluated` details using architecture precedence.

Every result includes:

- completion state and independent quality flags;
- hardware, firmware, protocol, limits, and adapter revisions;
- requested/completed repetitions;
- expected and observed groups as applicable;
- stable reason codes for any false quality flag;
- exactly one evidence context from the closed enum `host_simulation`, `device_observation`, `bench`, or `field_observation`. Firmware-originated physical scans use `bench` only when the surrounding test record records the controlled instruments, setup, conditions, and hardware revision; otherwise the app uses `device_observation`, which is not validation evidence.

A passing expected-map comparison requires all applicable quality flags true and no class other than `matched`.

### `progress`

Progress contains phase, monotonically non-decreasing `completed`, fixed positive `total`, and safe textual status code. Counters cannot exceed `total`. Progress is informational and cannot authorize state changes.

### `cancel` / `cancelled`

`cancel` is accepted for an active request. The device disables stimulus and reaches the safe condition before sending `cancelled`. Accumulated data is optional but, if returned, is marked partial, incomplete, and non-passing. Cancellation invalidates the precheck token.

### `error` and `fault`

Errors contain:

```json
{"code":"stable_machine_code","message":"short user-safe text","recoverable":true}
```

They exclude raw stack traces, paths, memory contents, and arbitrary echoed input. An `error` means a rejected command with no unsafe state change. A `fault` means the device entered/preserved `fault_safe`; recovery requires the documented action and a new precheck. Neither response can represent a pass.

Minimum codes include `invalid_frame`, `frame_too_large`, `invalid_schema`, `invalid_endpoint`, `duplicate_endpoint`, `duplicate_id`, `unsupported_version`, `incompatible_revision`, `invalid_state`, `limits_unavailable`, `precheck_required`, `precheck_expired`, `precheck_failed`, `self_test_failed`, `unexpected_voltage`, `cancelled`, and `internal_invariant`.

## State and safety invariants

- A scan/self-test is accepted only from `armed` after one passing, compatible, unexpired precheck.
- Fault, disconnect, cancel, watchdog/reset, malformed state-changing input, internal invariant failure, or observed unexpected voltage returns/preserves every bank node in the safe condition. Any rejected input while `armed` also invalidates the token and leaves `armed`.
- The host cannot override failed precheck, electrical limits, or hardware fault state.
- No message exposes raw GPIO selection, drive enable, arbitrary dwell, shell/script execution, or firmware update.
- Stimulus scheduling is one-node maximum, break-before-make, and bounded to 30 seconds per accepted scan.

## Privacy and text handling

There is no authentication or encryption because the MVP is a physical single-user USB connection, but both peers treat every frame as untrusted. There is no Wi-Fi, Bluetooth, internet listener, telemetry, remote control, shell, or cloud dependency.

Reports may contain user project names/notes; app export is explicit and can omit them and device identifiers. Firmware messages use stable codes and fixed user-safe text rather than echoing arbitrary input. Diagnostic logs exclude free-text notes unless the user explicitly enables a documented local diagnostic mode.
