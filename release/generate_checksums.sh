#!/usr/bin/env bash
# Regenerate SHA-256 checksums for the rev-A candidate release manifest.
# Run from the repository root:  bash release/generate_checksums.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
out="release/manifest-checksums.txt"
: > "$out"

paths=$(
  git ls-files \
    'hardware/pinpath.kicad_pro' 'hardware/pinpath.kicad_sch' \
    'hardware/pinpath.kicad_pcb' 'hardware/pinpath.kicad_sym' \
    'hardware/pinpath.pretty/**' 'hardware/TestPoint.pretty/**' \
    'hardware/adapters/known-loopback/**' \
    'hardware/requirements.md' 'hardware/selection/**' \
    'hardware/reports/**' 'hardware/fab-out/pinpath-gerbers/**' \
    'hardware/fab-out/pinpath-cpl.csv' 'hardware/fab-out/gerber-inspection.json' \
    'hardware/fab-out/renders/**' \
    'bom/bom.csv' 'bom/non-schematic-items.csv' \
    'firmware/src/**' 'firmware/tests/**' 'firmware/CMakeLists.txt' \
    'firmware/hil/**' 'firmware/third_party/**' \
    'app/src/**' 'app/src-tauri/src/**' 'app/package.json' \
    'app/package-lock.json' 'app/src-tauri/Cargo.toml' 'app/src-tauri/Cargo.lock' \
    'docs/**' 'LICENSE' 'THIRD_PARTY_NOTICES.md' 'README.md' 'PLAN.md'
)

# shellcheck disable=SC2086
sha256sum $paths >> "$out"
echo "wrote $out ($(wc -l < "$out") entries)"
