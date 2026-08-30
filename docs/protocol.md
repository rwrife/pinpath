# PinPath device/app protocol draft

## Transport and framing

Planned transport is USB CDC using newline-delimited UTF-8 JSON. Each frame is one JSON object with `v`, `type`, `id`, and a type-specific `payload`. The final implementation must cap line length, nesting depth, string length, and array counts before allocation.

This contract is provisional; there is no firmware or app implementation yet.

## Versioning

- `v`: positive protocol major version; MVP planning value is `1`.
- Unknown major versions are rejected without starting a scan.
- Additive optional fields may appear within one major version and must be ignored safely.
- Every command has an app-generated opaque `id`; responses echo it.

## Planned command flow

```text
app -> hello
app <- hello_result {hardware_revision, firmware_version, capabilities, state}
app -> precheck
app <- precheck_result {status, observations, limits_revision}
app -> self_test | scan {mode, expected_map?, repetitions?}
app <- progress {phase, completed, total}
app <- scan_result {observed_edges, opens, shorts, crossovers, unstable, quality}
app -> cancel
app <- cancelled | fault
```

`expected_map` is a list of canonical endpoints such as `A:01` and `B:01`, never arbitrary GPIO numbers. Firmware validates every endpoint and rejects duplicates or impossible mappings.

## Safety state machine

A scan command is accepted only from idle after a successful, recent precheck. Fault, disconnect, incompatible version, malformed command, cancellation, watchdog reset, or observed unexpected voltage returns every scan node to its documented safe state. The host cannot override a failed precheck.

## Security assumptions

- Physical, single-user USB connection; no authentication or encryption in MVP.
- No Wi-Fi, Bluetooth, internet listener, remote control, shell, script execution, or firmware update over this application protocol.
- Both sides treat input as untrusted and apply strict bounds and state validation.
- Reports may contain user-entered project names/notes; export is explicit and can redact those fields.
- The protocol cannot determine that a cable is safe to connect; safe use remains the operator's responsibility.

## Error model

Errors include a stable machine code, short user-safe message, and recoverability flag. Raw stack traces, paths, memory contents, and arbitrary echoed input are excluded. App and firmware logs must avoid serializing free-text notes unless diagnostic logging is explicitly enabled.
