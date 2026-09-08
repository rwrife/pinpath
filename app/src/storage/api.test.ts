import { describe, expect, it } from "vitest";
import {
  deleteProfile,
  exportBackup,
  exportReportsCsv,
  importBackup,
  listProfiles,
  saveReport,
  upsertProfile,
} from "./api";
import type { Profile, ScanReport } from "../types";

describe("storage API browser fallback", () => {
  it("stores profile/report data and supports backup/restore + csv", async () => {
    const profile: Profile = {
      id: "p-1",
      name: "Harness A",
      expectedGroups: [["A:01", "B:01"]],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      notes: "baseline",
    };

    await upsertProfile(profile);
    const storedProfiles = await listProfiles();
    expect(storedProfiles.some((entry) => entry.id === profile.id)).toBe(true);

    const report: ScanReport = {
      id: "r-1",
      profileId: profile.id,
      profileName: profile.name,
      mode: "expected",
      comparison: {
        matchedGroups: [["A:01", "B:01"]],
        openGroups: [],
        shortGroups: [],
        crossoverGroups: [],
        unstableGroups: [],
        unknownGroups: [],
        safeToProceed: true,
      },
      observation: {
        observedGroups: [["A:01", "B:01"]],
        unstableGroups: [],
        faults: [],
      },
      createdAt: new Date().toISOString(),
      hardwareRevision: "rev-a",
      firmwareVersion: "0.1.0",
      limitsRevision: "2026-09-01",
      protocolMajor: 1,
      protocolMinor: 0,
      precheckPassed: true,
      selfTestPassed: true,
      notes: "",
    };

    await saveReport(report);
    const csv = await exportReportsCsv();
    expect(csv).toContain("safe_to_proceed");
    expect(csv).toContain("Harness A");

    const backupJson = await exportBackup();
    const imported = await importBackup(backupJson);
    expect(imported.profiles).toBeGreaterThan(0);
    expect(imported.reports).toBeGreaterThan(0);

    await deleteProfile(profile.id);
  });
});
