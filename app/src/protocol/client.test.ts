import { describe, expect, it } from "vitest";
import { MockAdapter } from "../adapters/mockTransport";
import { DEFAULT_FIXTURES } from "../fixtures/defaultFixtures";
import { ProtocolClient } from "./client";

describe("protocol client handshake and scan", () => {
  it("requires precheck token immediately before scan", async () => {
    const adapter = new MockAdapter(DEFAULT_FIXTURES);
    const client = new ProtocolClient(adapter);

    await client.connect("fixture-pass");

    await expect(client.runScan("unknown", null, () => undefined)).rejects.toThrow(/precheck token/i);

    const precheck = await client.runPrecheck();
    expect(precheck.pass).toBe(true);

    const report = await client.runScan("unknown", null, () => undefined);
    expect(report.comparison.safeToProceed).toBe(true);

    await expect(client.runScan("unknown", null, () => undefined)).rejects.toThrow(/precheck token/i);
  });

  it("rejects incompatible protocol major", async () => {
    const adapter = new MockAdapter(DEFAULT_FIXTURES);
    const client = new ProtocolClient(adapter);

    await expect(client.connect("fixture-incompatible")).rejects.toThrow(/protocol incompatibility/i);
  });
});
