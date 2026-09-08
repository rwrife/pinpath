# USB permission behavior for PinPath companion

This document records expected OS-level USB serial permission behavior for development builds.

## Linux

- Most distributions expose USB CDC devices as `/dev/ttyACM*` or `/dev/ttyUSB*`.
- Access typically requires membership in groups such as `dialout` or an explicit udev rule.
- Baseline udev pattern (adapt VID/PID after final hardware IDs are known):

```udev
SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{idProduct}=="000a", MODE:="0660", GROUP:="dialout", TAG+="uaccess"
```

After rules change: `sudo udevadm control --reload-rules && sudo udevadm trigger` and reconnect hardware.

## macOS

- CDC ACM devices usually attach without third-party drivers.
- On managed systems, serial access can still be constrained by policy.
- App remains user-initiated: no automatic background polling of USB ports.

## Windows 10/11

- CDC/WinUSB drivers may auto-install on first plug-in.
- Managed endpoints can restrict driver installation and COM-port visibility.
- App should surface actionable errors when ports are unavailable instead of retry loops.

## Security and privacy posture

- USB and filesystem actions are explicit user actions only.
- No network service, cloud storage, account identity, or telemetry channel is required.
- Device text is treated as untrusted input and sanitized before rendering/export.

## Packaging status

Unsigned development artifacts are built in CI to verify reproducibility. Code signing and notarization are tracked as a future milestone and are not claimed yet.
