import type { Endpoint, ScanComparison, ScanObservation } from "../types";

function groupKey(group: Endpoint[]): string {
  return [...group].sort().join(",");
}

function normalizeGroups(groups: Endpoint[][]): Endpoint[][] {
  return groups.map((group) => [...group].sort());
}

function expectedPartnerMap(groups: Endpoint[][]): Map<Endpoint, Endpoint> {
  const mapping = new Map<Endpoint, Endpoint>();
  for (const group of groups) {
    if (group.length !== 2) {
      continue;
    }
    const [a, b] = group;
    mapping.set(a, b);
    mapping.set(b, a);
  }
  return mapping;
}

function groupsShareExpectedDomain(group: Endpoint[], expected: Endpoint[][]): boolean {
  const expectedByEndpoint = new Map<Endpoint, number>();
  expected.forEach((entry, index) => {
    for (const endpoint of entry) {
      expectedByEndpoint.set(endpoint, index);
    }
  });
  const buckets = new Set<number>();
  for (const endpoint of group) {
    const idx = expectedByEndpoint.get(endpoint);
    if (typeof idx === "number") {
      buckets.add(idx);
    }
  }
  return buckets.size > 1;
}

export function compareObservedToExpected(
  expectedGroups: Endpoint[][],
  observation: ScanObservation,
): ScanComparison {
  const expected = normalizeGroups(expectedGroups);
  const observed = normalizeGroups(observation.observedGroups);
  const unstable = normalizeGroups(observation.unstableGroups);

  const expectedKeys = new Set(expected.map(groupKey));
  const observedKeys = new Set(observed.map(groupKey));
  const matchedGroups = expected.filter((group) => observedKeys.has(groupKey(group)));

  const partnerMap = expectedPartnerMap(expected);
  const crossoverGroups: Endpoint[][] = [];
  for (const group of observed) {
    if (group.length !== 2) {
      continue;
    }
    const [a, b] = group;
    const expectedA = partnerMap.get(a);
    const expectedB = partnerMap.get(b);
    if (
      expectedA &&
      expectedB &&
      expectedA !== b &&
      expectedB !== a &&
      !expectedKeys.has(groupKey(group))
    ) {
      crossoverGroups.push(group);
    }
  }

  const shortGroups = observed.filter((group) => group.length > 2 || groupsShareExpectedDomain(group, expected));

  const openGroups = expected.filter((group) => {
    const key = groupKey(group);
    return !observedKeys.has(key) && !crossoverGroups.some((entry) => group.some((p) => entry.includes(p)));
  });

  const unknownGroups = observed.filter((group) => {
    const key = groupKey(group);
    return !expectedKeys.has(key) && !crossoverGroups.some((entry) => groupKey(entry) === key) && !shortGroups.some((entry) => groupKey(entry) === key);
  });

  const unstableGroups = unstable;

  const hardFaults = new Set(observation.faults);
  const safeToProceed =
    openGroups.length === 0 &&
    shortGroups.length === 0 &&
    crossoverGroups.length === 0 &&
    unstableGroups.length === 0 &&
    hardFaults.size === 0;

  return {
    matchedGroups,
    openGroups,
    shortGroups,
    crossoverGroups,
    unstableGroups,
    unknownGroups,
    safeToProceed,
  };
}

export function parseEndpoint(value: string): Endpoint {
  if (!/^[AB]:\d{2}$/.test(value)) {
    throw new Error(`endpoint '${value}' is invalid`);
  }
  return value as Endpoint;
}

export function parseExpectedGroups(input: string): Endpoint[][] {
  const parsed: unknown = JSON.parse(input);
  if (!Array.isArray(parsed)) {
    throw new Error("expected groups must be a JSON array");
  }
  return parsed.map((entry, idx) => {
    if (!Array.isArray(entry)) {
      throw new Error(`group at index ${idx} is not an array`);
    }
    return entry.map((raw, endpointIndex) => {
      if (typeof raw !== "string") {
        throw new Error(`endpoint at group ${idx} index ${endpointIndex} must be a string`);
      }
      return parseEndpoint(raw);
    });
  });
}

export function parseObservedGroups(input: unknown): Endpoint[][] {
  if (!Array.isArray(input)) {
    throw new Error("observed groups must be an array");
  }
  return input.map((entry, idx) => {
    if (!Array.isArray(entry)) {
      throw new Error(`observed group at index ${idx} is not an array`);
    }
    return entry.map((raw, endpointIndex) => {
      if (typeof raw !== "string") {
        throw new Error(`observed endpoint at group ${idx} index ${endpointIndex} must be a string`);
      }
      return parseEndpoint(raw);
    });
  });
}

export function containsUnstable(unstableGroups: Endpoint[][]): boolean {
  return unstableGroups.length > 0;
}
