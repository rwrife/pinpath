# PinPath rev-A carrier PCB — layout evidence and adjudication (issue #4)

Status: **fabrication candidate — release-candidate quality only.** Nothing on
this board has been fabricated, assembled, or bench-tested. All evidence below
is static EDA analysis, native DRC, and heuristic analyzer output. This board
must NOT be ordered or powered up on the strength of these checks; physical
bring-up gates stay open in issue #7.

## Board snapshot

- File: `hardware/pinpath.kicad_pcb` (KiCad 9.0.9, 2 copper layers)
- Outline: 96.0 × 76.0 mm closed Edge.Cuts rectangle
- 160 footprints (142 SMD / 14 THT, 4 mounting holes), 2,399 track segments,
  375 through vias, 6 zones (GND pours on F.Cu+B.Cu, 4 mounting-hole keepout
  pockets)
- Silk: `BANK A`, `BANK B`, `PinPath rev-A`, `SWD`, and a hard
  `DE-ENERGIZED CABLES ONLY` safety banner; J1/J2 pin-1 landmarks at
  (39.2, 9.5) / (68.6, 9.5)
- Testability: 12 micro test points (TP1–TP12) on supply rails, precheck
  bias, and SWD
- Design rules committed in `hardware/pinpath.kicad_pro`: min clearance
  0.2 mm, min via drill 0.3 mm / annular start 0.15→0.6 mm default, min
  copper-edge clearance 0.5 mm, min hole clearance 0.25 mm

## Grounding / return-path / fault-current rationale

- Single ground domain (`/GND`): USB/shield, Pico, mux GNDs, clamp returns,
  and bank connector shields terminate on one F.Cu+B.Cu pour pair. No split
  analog/digital domains — the front end is passive-biased and low-current,
  and a split would only create return-path crossings.
- Return paths: signal stubs are short fanouts from the mux rows to the bank
  connectors; the DRC-clean pass keeps each scan node hop over contiguous
  pour except the documented residual islands below.
- Fault currents: every one of the 32 bank endpoints is series-limited by
  10 kΩ at the clamp stage before any mux path (per rev-A schematic), so the
  injected precheck current is µA-class; the pour and 0.2–0.3 mm traces never
  carry harness-fault energy, and protection clamp returns land directly on
  the pour adjacent to each clamp.
- USB: VBUS enters only at the Pico connector; no VBUS fanout exists on the
  board, so USB return current has a single short path into the pour under
  the module.

## Verification performed (all on the committed board state)

Commands (KiCad 9.0.9 via the pinned container):

```
kicad-cli pcb drc --format json --severity-error --severity-warning \
    --output reports/drc-20260918-final.json pinpath.kicad_pcb
kicad-cli sch export netlist pinpath.kicad_sch -o reports/pinpath-20260918.net
python3 hardware/scripts/verify_pad_nets.py pinpath.kicad_pcb \
    reports/pinpath-20260918.net
analyze_schematic.py / analyze_pcb.py --full / cross_analysis.py /
analyze_thermal.py / analyze_emc.py → analysis/2026-09-17_0618/
kicad-cli pcb export gerbers / drill / pos --units mm → fab-out/
analyze_gerbers.py fab-out/pinpath-gerbers → fab-out/gerber-inspection.json
```

Results:

- **Native DRC: 0 errors.** 63 warnings: 44 `lib_footprint_mismatch`
  (intentional embedded-copy tuning — see exceptions), 13 `silk_overlap` +
  4 `silk_over_copper` (dense-board silk cosmetics), 2 `hole_to_hole`
  (TP3 drill vs adjacent GND stitching via, 0.24 mm < 0.25 mm rule —
  documented below).
- **Ratsnest: 66 unconnected items = 65 same-zone pseudo-ratsnest pairs
  (fragmented pour islands) + 1 real stub.** The real stub is
  `U9.2 (/SENSE_HI_EN)`: FreeRouter, the deterministic cross-layer closer,
  and the grid-A* rerouter (`--net SENSE_HI_EN`, result `R70.1->U9.2 no
  path`) all fail. Cause is arithmetic, not router effort: U9 is 0.65 mm
  TSSOP-16 with 0.4 mm pads; the 0.25 mm inter-pad corridor is smaller than
  the minimum legal track+clearance corridor (0.39 mm even at the relaxed
  0.13/0.13 mm fanout rules), so no capsule can legally thread the final
  hop. Fix path: net-class-local clearance relaxation with vendor DFM
  confirmation, or a pad-sweep fanout — deferred as a rev-A residual.
- **Pad-to-net parity: 531/531 schematic pads agree with PCB pads (0 net
  mismatches).** 30 board-only pads carry no net and are mounting-hole/
  shield/unused-by-design pads (H1–H4, J1/J2 shields, J3.6–8, U1 shell/NC
  pads, D33–D40 pad 5) — verified netless, not wired wrong.
- **Schematic ERC: 0 errors / 0 warnings** (`reports/pinpath-erc.rpt`,
  carried from issue #3; schematic unchanged since).
- **Gerber/drill inspection:** complete 9-layer stack + PTH/NPTH drill,
  drill classified 375 via holes (0.30 mm), 48 component holes, 8 mounting
  holes; board 96.05×76.05 mm from gbrjob. GR-002 "width varies 12.5 mm"
  is the empty B.Paste/B.SilkS extent artifact (layers legitimately have
  no items) — copper/edge extents agree.
- **Thermal analyzer: 0 findings** — the whole design is µA–mA class; no
  package dissipates enough to model.
- **Cross-domain/EMC analyzers:** findings concentrated on the same pour-
  island residual (RP-002 SWCLK plane gap, PS-002 island count, GP-001
  family). These are heuristic heuristics (`trust: low/mixed`), NOT bench
  EMC data; the physical residual is identical to the ratsnest one above.

## Intentional exceptions (explicit, not silent)

1. `lib_footprint_mismatch` ×44 — embedded footprint copies were pad-tuned
   for routing (pitfall 19: refreshing to stock library copies introduced
   hard shorts/clearance errors, so the tuned embedded copies are kept).
2. Pour-island pseudo-ratsnest ×65 + `hole_to_hole` ×2 + EMC plane-gap
   family — GND pour fragmentation from 0.3 mm-clearance stitching vias.
   Per pitfall 49, naive stitch passes injected new hard errors and were
   reverted; conservative v3 stitching placed 1 of 66 islands and is kept.
   Named fix: wider pour corridors in rev-B. Residual is acceptable for a
   µA-class passive mapper but is a legitimate rev-B item.
3. Edge connectors — J1/J2 courtyards intentionally overhang to give harness
   access (PM-002 analyzer warnings); native copper-edge-clearance is clean.
4. Mounting holes inside their own keepout pockets (KO-001 analyzer
   warnings) — by design: the pockets carve copper from the hole annulus;
   rule-area flags permit the hole pad/track/via (pitfall 33).
5. `U9.2` fanout stub — physics-gated, see above. Board is NOT fab-ready
   until a rev-B rule/pad decision resolves it.

## Fabrication posture

`fab-out/` holds a full export set (Gerbers + drill + CPL in mm) with
`gerber-inspection.json` review output. These are **release candidates
only**: they have not been ordered, no fab has accepted them, and no
assembly tier/cost claim is made. Preliminary capability view from
measured geometry (0.2 mm tracks / 0.3 mm drills / 0.2 mm clearance):
within standard 2-layer tier of typical low-cost fabs — a geometry
observation, not a quote.

## Adapter decision

The first adapter remains a **passive cable assembly, not a PCB**: the
known-loopback fixture (`hardware/adapters/known-loopback/`) is a
one-to-one 16-position A↔B loopback with canonical numbering, defined
electrically and verified in its own ERC report. A dedicated adapter PCB
adds no function for the fixture use-case and its own fab/DRC surface;
a justification for cable over PCB is recorded in
`hardware/adapters/known-loopback/adapter-manifest.json`
(`physical_evidence: none; ... issue #4/#7 gates`). Crimp tooling, wire
gauge, keying, and continuity of a built fixture remain **bench evidence
still owed by issue #7** — this is a static definition, not a validated
fixture.

## Reproduction

Pipeline scripts used are committed under `hardware/scripts/`; router
DSN/SES transcripts under `hardware/router/`; raw DRC/import/refill/stitch
logs under `hardware/reports/`. `kicad-cli` and pcbnew scripts run in the
`parts-tally-kicad:9-arm64` image (repo-local `kicad-cli` wrapper).
Analyzer scripts are the kicad skill's (`analyze_schematic.py`,
`analyze_pcb.py --full`, `cross_analysis.py`, `analyze_thermal.py`,
`analyze_emc.py`, `analyze_gerbers.py`).
