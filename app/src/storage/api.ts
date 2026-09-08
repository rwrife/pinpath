import { invoke } from "@tauri-apps/api/core";
import type { BackupPayload, Profile, ScanReport } from "../types";
import { sanitizeText } from "../protocol/frameValidation";

interface DatabaseSnapshot {
  profiles: Profile[];
  reports: ScanReport[];
}

const STORAGE_KEY = "pinpath.local.snapshot.v1";

function inTauriRuntime(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

function loadLocalSnapshot(): DatabaseSnapshot {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return { profiles: [], reports: [] };
  }
  try {
    const parsed = JSON.parse(raw) as DatabaseSnapshot;
    return {
      profiles: Array.isArray(parsed.profiles) ? parsed.profiles : [],
      reports: Array.isArray(parsed.reports) ? parsed.reports : [],
    };
  } catch {
    return { profiles: [], reports: [] };
  }
}

function saveLocalSnapshot(snapshot: DatabaseSnapshot): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

export async function listProfiles(): Promise<Profile[]> {
  if (inTauriRuntime()) {
    return invoke<Profile[]>("list_profiles");
  }
  return loadLocalSnapshot().profiles;
}

export async function upsertProfile(profile: Profile): Promise<Profile> {
  if (inTauriRuntime()) {
    return invoke<Profile>("upsert_profile", { profile });
  }
  const snapshot = loadLocalSnapshot();
  const idx = snapshot.profiles.findIndex((entry) => entry.id === profile.id);
  if (idx >= 0) {
    snapshot.profiles[idx] = profile;
  } else {
    snapshot.profiles.push(profile);
  }
  saveLocalSnapshot(snapshot);
  return profile;
}

export async function deleteProfile(profileId: string): Promise<void> {
  if (inTauriRuntime()) {
    await invoke<void>("delete_profile", { profile_id: profileId });
    return;
  }
  const snapshot = loadLocalSnapshot();
  snapshot.profiles = snapshot.profiles.filter((entry) => entry.id !== profileId);
  snapshot.reports = snapshot.reports.filter((entry) => entry.profileId !== profileId);
  saveLocalSnapshot(snapshot);
}

export async function listReports(): Promise<ScanReport[]> {
  if (inTauriRuntime()) {
    return invoke<ScanReport[]>("list_reports");
  }
  return loadLocalSnapshot().reports;
}

export async function saveReport(report: ScanReport): Promise<ScanReport> {
  if (inTauriRuntime()) {
    return invoke<ScanReport>("upsert_report", { report });
  }
  const snapshot = loadLocalSnapshot();
  const idx = snapshot.reports.findIndex((entry) => entry.id === report.id);
  if (idx >= 0) {
    snapshot.reports[idx] = report;
  } else {
    snapshot.reports.unshift(report);
  }
  saveLocalSnapshot(snapshot);
  return report;
}

export async function deleteReport(reportId: string): Promise<void> {
  if (inTauriRuntime()) {
    await invoke<void>("delete_report", { report_id: reportId });
    return;
  }
  const snapshot = loadLocalSnapshot();
  snapshot.reports = snapshot.reports.filter((entry) => entry.id !== reportId);
  saveLocalSnapshot(snapshot);
}

export async function exportBackup(): Promise<string> {
  if (inTauriRuntime()) {
    return invoke<string>("export_backup_json");
  }
  const snapshot = loadLocalSnapshot();
  const backup: BackupPayload = {
    schemaVersion: 1,
    exportedAt: new Date().toISOString(),
    profiles: snapshot.profiles,
    reports: snapshot.reports,
  };
  return JSON.stringify(backup, null, 2);
}

export async function importBackup(jsonPayload: string): Promise<{ profiles: number; reports: number }> {
  if (inTauriRuntime()) {
    return invoke<{ profiles: number; reports: number }>("import_backup_json", { json_payload: jsonPayload });
  }
  const parsed = JSON.parse(jsonPayload) as BackupPayload;
  const snapshot = loadLocalSnapshot();
  snapshot.profiles = parsed.profiles;
  snapshot.reports = parsed.reports;
  saveLocalSnapshot(snapshot);
  return { profiles: parsed.profiles.length, reports: parsed.reports.length };
}

export async function exportReportsCsv(): Promise<string> {
  if (inTauriRuntime()) {
    return invoke<string>("export_reports_csv");
  }
  const reports = loadLocalSnapshot().reports;
  const header = [
    "id",
    "created_at",
    "profile_name",
    "mode",
    "safe_to_proceed",
    "hardware_revision",
    "firmware_version",
    "faults",
  ];
  const rows = reports.map((report) => [
    report.id,
    report.createdAt,
    report.profileName,
    report.mode,
    String(report.comparison.safeToProceed),
    report.hardwareRevision,
    report.firmwareVersion,
    report.observation.faults.join(";"),
  ]);

  const escapeCsv = (value: unknown): string => {
    const sanitized = String(sanitizeText(value));
    return `"${sanitized.split('"').join('""')}"`;
  };

  return [header, ...rows]
    .map((row) => row.map((value) => escapeCsv(value)).join(","))
    .join("\n");
}
