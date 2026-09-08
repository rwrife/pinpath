import type { Endpoint, MatrixCell, ScanComparison } from "../types";

function endpointIndex(endpoint: Endpoint): { side: "A" | "B"; idx: number } {
  const side = endpoint[0] as "A" | "B";
  const idx = Number.parseInt(endpoint.slice(2), 10);
  return { side, idx };
}

function emptyCell(row: number, col: number): MatrixCell {
  return {
    row,
    col,
    classification: "unknown",
    text: "·",
    ariaLabel: `A:${String(row + 1).padStart(2, "0")} to B:${String(col + 1).padStart(2, "0")}: not observed`,
  };
}

function setCell(cells: MatrixCell[], row: number, col: number, classification: MatrixCell["classification"], text: string, label: string): void {
  const idx = row * 16 + col;
  cells[idx] = { row, col, classification, text, ariaLabel: label };
}

function applyGroups(cells: MatrixCell[], groups: Endpoint[][], classification: MatrixCell["classification"], text: string, labelPrefix: string): void {
  for (const group of groups) {
    const aEndpoints = group.map(endpointIndex).filter((entry) => entry.side === "A");
    const bEndpoints = group.map(endpointIndex).filter((entry) => entry.side === "B");
    for (const a of aEndpoints) {
      for (const b of bEndpoints) {
        if (a.idx < 1 || a.idx > 16 || b.idx < 1 || b.idx > 16) {
          continue;
        }
        const row = a.idx - 1;
        const col = b.idx - 1;
        setCell(
          cells,
          row,
          col,
          classification,
          text,
          `${labelPrefix}: A:${String(a.idx).padStart(2, "0")} to B:${String(b.idx).padStart(2, "0")}`,
        );
      }
    }
  }
}

export function buildMatrix(comparison: ScanComparison): MatrixCell[] {
  const cells: MatrixCell[] = [];
  for (let row = 0; row < 16; row += 1) {
    for (let col = 0; col < 16; col += 1) {
      cells.push(emptyCell(row, col));
    }
  }

  applyGroups(cells, comparison.matchedGroups, "pass", "✓", "match");
  applyGroups(cells, comparison.openGroups, "open", "O", "open");
  applyGroups(cells, comparison.shortGroups, "short", "S", "short");
  applyGroups(cells, comparison.crossoverGroups, "crossover", "X", "crossover");
  applyGroups(cells, comparison.unstableGroups, "unstable", "!", "unstable");
  applyGroups(cells, comparison.unknownGroups, "unknown", "?", "unexpected");

  return cells;
}
