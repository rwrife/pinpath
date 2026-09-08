import { describe, expect, it } from "vitest";
import { compareObservedToExpected } from "./comparison";

describe("expected vs observed comparison", () => {
  const expected = [
    ["A:01", "B:01"],
    ["A:02", "B:02"],
  ] as const;

  it("classifies perfect match as safe", () => {
    const result = compareObservedToExpected(
      expected.map((entry) => [...entry]),
      {
        observedGroups: expected.map((entry) => [...entry]),
        unstableGroups: [],
        faults: [],
      },
    );

    expect(result.safeToProceed).toBe(true);
    expect(result.openGroups).toHaveLength(0);
    expect(result.shortGroups).toHaveLength(0);
  });

  it("detects crossover and short groups", () => {
    const result = compareObservedToExpected(
      expected.map((entry) => [...entry]),
      {
        observedGroups: [
          ["A:01", "B:02"],
          ["A:02", "B:01", "B:03"],
        ],
        unstableGroups: [["A:03", "B:04"]],
        faults: [],
      },
    );

    expect(result.crossoverGroups.length).toBeGreaterThanOrEqual(1);
    expect(result.shortGroups.length).toBeGreaterThanOrEqual(1);
    expect(result.unstableGroups).toHaveLength(1);
    expect(result.safeToProceed).toBe(false);
  });
});
