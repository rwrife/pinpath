# PinPath BOM

`bom/bom.csv` is a tracked native KiCad CLI export from `hardware/pinpath.kicad_sch`. The schematic symbol properties are the source of truth for Manufacturer, MPN, Datasheet, Supplier, source URL, estimated unit cost, and BOM comments.

Regenerate it from the repository root with:

```bash
kicad-cli sch export bom hardware/pinpath.kicad_sch \
  -o bom/bom.csv \
  --fields 'Reference,${QUANTITY},Value,Footprint,Manufacturer,MPN,Supplier,Source URL,Estimated Unit Cost USD,Datasheet,BOM Comments,Evidence Status' \
  --labels 'References,Quantity,Value or Description,Footprint or Package,Manufacturer,MPN,Supplier,Source URL,Estimated Unit Cost USD,Datasheet,Notes,Evidence Status' \
  --group-by 'Value,Footprint,Manufacturer,MPN,Supplier,Estimated Unit Cost USD' \
  --sort-field Reference --exclude-dnp
```

`bom/non-schematic-items.csv` tracks mating housings/contacts, programming tools, cables, and mechanical items that do not belong as carrier schematic symbols.

All current unit-cost cells are deliberately `UNKNOWN`: no current quantity-specific authorized-distributor quote was obtained. Neither CSV is an order file, stock statement, lifecycle validation, or claim that hardware has been assembled.

## Sourcing status (issue #7 roll-up, 2026-09-19)

- **Schematic-property coverage:** every carrier BOM line carries Manufacturer, MPN, package, source URL, and an `Evidence Status` note; `bom/bom.csv` was re-exported from the schematic on 2026-09-19 and is byte-identical to the committed file.
- **Availability/lifecycle observations:** last recorded 2026-09-01 in `hardware/selection/availability-2026-09-01.csv` (public listings only; no quantity price captured, no authorized-stock confirmation, no lifecycle certificate). **No re-validation has been performed since that date; these observations are stale for ordering purposes and must be refreshed before any purchase.**
- **Unresolved cost gaps:** every unit-cost cell in both CSVs is `UNKNOWN` by design — no authorized-distributor quote at order quantity has been obtained. No price in this repository may be treated as a quote.
- **Substitutions:** none approved. Any substitution requires datasheet-level review and a schematic-property change before re-export (see the re-export command above).
- **Non-schematic items:** `bom/non-schematic-items.csv` tracks mating housings (`43025-1600`), crimp contacts (`43030-0007`, tooling unconfirmed), the candidate SWD probe (`SC0889`, adapter cable not yet selected), USB cable, and enclosure/fasteners (issue #4/#7 mechanical selection pending). Assembly notes for these items live in `docs/assembly-guide.md`.
