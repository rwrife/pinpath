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
