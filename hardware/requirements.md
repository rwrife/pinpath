# Hardware requirements (draft)

All values marked **TARGET** are design requirements to validate; they are not measured results.

## Electrical

- **TARGET:** USB 5 V SELV input only; no battery or external power-input mode.
- **TARGET:** 16 test positions on Bank A and 16 on Bank B.
- **TARGET:** scan only after a passed unexpected-voltage precheck and explicit user/device action.
- **TARGET:** one driven test node at a time; all others high impedance except defined bias/sense networks.
- **TARGET:** detect direct opens, single/multiple crossovers, and shorts among exposed test positions under a datasheet-backed resistance threshold.
- **TARGET:** drive current and exposure duration remain within selected MCU/front-end ratings under any allowed node short.
- **TARGET:** reverse/ESD protection appropriate to bench handling; no claim of surviving prohibited live-voltage connection.
- **TARGET:** named test points for USB input, logic rail, ground, scan control, status, and representative test-bank channels.

## Mechanical

- **TARGET:** main PCB no larger than 100 mm × 80 mm unless connector spacing evidence requires otherwise.
- **TARGET:** four mounting points or equivalent retained enclosure support.
- **TARGET:** keyed/marked test-bank connectors with visible Bank, position, and pin-1 labeling.
- **TARGET:** adapters replaceable without soldering the main board.
- **TARGET:** enclosure opens with common hand tools and does not depend on adhesive for routine service.

## Environmental and use

- Indoor bench use in a dry, ordinary room environment only.
- No outdoor, condensing, wet, dusty-industrial, vehicle, or high-vibration rating.
- Human-supervised operation; no unattended or safety-interlock role.
- Store and transport disconnected from the item under test.

## Connectivity and data

- USB CDC with an explicit protocol version and maximum message size.
- Core map/profile comparison must work without network access.
- Device remains useful through a text serial client if the companion app is unavailable.
- No unique device identifier is exported unless the user explicitly includes it in a report.

## Cost and sourcing

- **Planning target:** USD 35–60 for one prototype including controller, carrier, first passive adapter, enclosure materials, ordinary cable, and fasteners.
- **Ceiling:** USD 75 excluding the host computer, tools, shipping/tax, and specialized connector adapters.
- Exact prices, stock, lifecycle, package, and MPNs are TBD until live sourcing and manufacturer-datasheet validation.
- Prefer parts available from at least two reputable distributors when practical and packages suitable for documented home assembly or assembly-house placement.

## Verification

Requirements close only with cited datasheets, KiCad ERC/DRC output, firmware/app builds and tests, or measured bench evidence as applicable. Static analysis, simulation, and physical measurements must be labeled separately.
