#!/usr/bin/env python3
"""Export Specctra DSN for the pinpath board (run inside parts-tally-kicad).

Usage: export_dsn.py <board.kicad_pcb> <out.dsn>
"""
import sys

import pcbnew

board = pcbnew.LoadBoard(sys.argv[1])
ok = pcbnew.ExportSpecctraDSN(board, sys.argv[2])
print("dsn_export", ok)
sys.exit(0 if ok else 1)
