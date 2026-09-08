import { describe, expect, it } from "vitest";
import { MockAdapter } from "../adapters/mockTransport";
import { DEFAULT_FIXTURES } from "../fixtures/defaultFixtures";
import { ProtocolClient } from "./client";

async function runFixtureScan(fixtureId: string) {
  const adapter = new MockAdapter(DEFAULT_FIXTURES);
  const client = new ProtocolClient(adapter);
  await client.connect(fixtureId);
  await client.runPrecheck();
  return client.runScan(
    "expected",
    {
      id: "profile-1",
      name: "fixture-profile",
      expectedGroups: [
        ["A:01", "B:01"],
        ["A:02", "B:02"],
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      notes: "",
    },
    () => undefined,
  );
}

describe("deterministic protocol fixtures", () => {
  it("covers success mapping", async () => {
    const report = await runFixtureScan("fixture-pass");
    expect(report.comparison.safeToProceed).toBe(true);
    expect(report.comparison.matchedGroups).toHaveLength(2);
  });

  it("covers open-circuit mapping", async () => {
    const report = await runFixtureScan("fixture-open");
    expect(report.comparison.openGroups.length).toBeGreaterThan(0);
    expect(report.comparison.safeToProceed).toBe(false);
  });

  it("covers short/crossover/unstable mapping", async () => {
    const report = await runFixtureScan("fixture-faulty");
    expect(report.comparison.shortGroups.length).toBeGreaterThan(0);
    expect(report.comparison.crossoverGroups.length).toBeGreaterThan(0);
    expect(report.comparison.unstableGroups.length).toBeGreaterThan(0);
    expect(report.selfTestPassed).toBe(false);
  });

  it("covers disconnect fault", async () => {
    await expect(runFixtureScan("fixture-disconnect")).rejects.toThrow(/device_disconnected/i);
  });

  it("covers stale precheck token", async () => {
    const adapter = new MockAdapter(DEFAULT_FIXTURES);
    const client = new ProtocolClient(adapter);

    await client.connect("fixture-pass");
    await client.runPrecheck();
    await client.runScan("unknown", null, () => undefined);

    await expect(client.runScan("unknown", null, () => undefined)).rejects.toThrow(/precheck token/i);
  });

  it("covers incompatible protocol handshake", async () => {
    const adapter = new MockAdapter(DEFAULT_FIXTURES);
    const client = new ProtocolClient(adapter);
    await expect(client.connect("fixture-incompatible")).rejects.toThrow(/protocol incompatibility/i);
  });
});
