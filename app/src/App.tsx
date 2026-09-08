import { useEffect, useMemo, useState } from "react";
import { MockAdapter } from "./adapters/mockTransport";
import { DEFAULT_FIXTURES } from "./fixtures/defaultFixtures";
import { buildMatrix } from "./logic/matrix";
import { parseExpectedGroups } from "./logic/comparison";
import { ProtocolClient } from "./protocol/client";
import { sanitizeText } from "./protocol/frameValidation";
import {
  deleteProfile,
  deleteReport,
  exportBackup,
  exportReportsCsv,
  importBackup,
  listProfiles,
  listReports,
  saveReport,
  upsertProfile,
} from "./storage/api";
import type { DeviceHello, Profile, ScanReport } from "./types";

import "./styles.css";

const adapter = new MockAdapter(DEFAULT_FIXTURES);
const client = new ProtocolClient(adapter);

function defaultExpectedTemplate(): string {
  return JSON.stringify(
    [
      ["A:01", "B:01"],
      ["A:02", "B:02"],
    ],
    null,
    2,
  );
}

function freshProfileDraft(): Omit<Profile, "createdAt" | "updatedAt"> & { expectedGroupsJson: string } {
  return {
    id: crypto.randomUUID(),
    name: "",
    notes: "",
    expectedGroups: [],
    expectedGroupsJson: defaultExpectedTemplate(),
  };
}

function summarize(report: ScanReport): string {
  const c = report.comparison;
  return [
    `match ${c.matchedGroups.length}`,
    `open ${c.openGroups.length}`,
    `short ${c.shortGroups.length}`,
    `crossover ${c.crossoverGroups.length}`,
    `unstable ${c.unstableGroups.length}`,
  ].join(" · ");
}

export default function App(): JSX.Element {
  const [ports, setPorts] = useState<Array<{ id: string; label: string }>>([]);
  const [selectedPort, setSelectedPort] = useState<string>("");
  const [hello, setHello] = useState<DeviceHello | null>(null);
  const [status, setStatus] = useState<string>("Disconnected. Discover a USB adapter to continue.");
  const [progress, setProgress] = useState<{ percent: number; stage: string }>({ percent: 0, stage: "idle" });
  const [scanMode, setScanMode] = useState<"unknown" | "expected">("expected");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>("");
  const [draft, setDraft] = useState(freshProfileDraft());
  const [reports, setReports] = useState<ScanReport[]>([]);
  const [activeReport, setActiveReport] = useState<ScanReport | null>(null);
  const [precheckTokenReady, setPrecheckTokenReady] = useState<boolean>(false);
  const [busy, setBusy] = useState<boolean>(false);

  const matrix = useMemo(() => (activeReport ? buildMatrix(activeReport.comparison) : []), [activeReport]);

  useEffect(() => {
    void refreshData();
  }, []);

  async function refreshData(): Promise<void> {
    const [nextProfiles, nextReports] = await Promise.all([listProfiles(), listReports()]);
    setProfiles(nextProfiles);
    setReports(nextReports);
  }

  async function handleDiscover(): Promise<void> {
    setBusy(true);
    try {
      const discovered = await client.discover();
      setPorts(discovered);
      if (discovered.length > 0) {
        setSelectedPort(discovered[0].id);
      }
      setStatus(`Discovered ${discovered.length} candidate USB interfaces.`);
    } catch (error) {
      setStatus(`Discovery failed: ${sanitizeText(String(error))}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleConnect(): Promise<void> {
    if (!selectedPort) {
      setStatus("Select a USB interface before connecting.");
      return;
    }
    setBusy(true);
    try {
      const details = await client.connect(selectedPort);
      setHello(details);
      setPrecheckTokenReady(false);
      setStatus(
        `Connected to ${sanitizeText(selectedPort)}. Protocol ${details.protocolMajor}.${details.protocolMinor}, firmware ${sanitizeText(details.firmwareVersion)}.`
      );
      await refreshData();
    } catch (error) {
      setHello(null);
      setStatus(`Connection rejected: ${sanitizeText(String(error))}`);
    } finally {
      setBusy(false);
    }
  }

  async function handlePrecheck(): Promise<void> {
    setBusy(true);
    try {
      const result = await client.runPrecheck();
      setPrecheckTokenReady(Boolean(result.pass && result.token));
      setStatus(result.pass ? "Precheck passed. Start scan now." : `Precheck failed: ${sanitizeText(result.detail)}`);
    } catch (error) {
      setPrecheckTokenReady(false);
      setStatus(`Precheck error: ${sanitizeText(String(error))}`);
    } finally {
      setBusy(false);
    }
  }

  async function handleScan(): Promise<void> {
    if (!hello) {
      setStatus("Connect to a compatible PinPath unit before scanning.");
      return;
    }
    if (!precheckTokenReady) {
      setStatus("Run precheck immediately before scan.");
      return;
    }
    setBusy(true);
    try {
      const profile = scanMode === "expected" ? profiles.find((entry) => entry.id === selectedProfileId) ?? null : null;
      if (scanMode === "expected" && !profile) {
        setStatus("Select a profile for expected-mode scan.");
        return;
      }
      const report = await client.runScan(scanMode, profile, setProgress);
      const stored = await saveReport(report);
      setActiveReport(stored);
      setReports((prev) => [stored, ...prev.filter((entry) => entry.id !== stored.id)]);
      setPrecheckTokenReady(false);
      setStatus(`Scan complete: ${summarize(stored)}.`);
    } catch (error) {
      setStatus(`Scan failed safely: ${sanitizeText(String(error))}`);
      setPrecheckTokenReady(false);
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel(): Promise<void> {
    try {
      await client.cancelScan();
      setStatus("Scan cancelled. Returned to safe idle state.");
      setBusy(false);
      setPrecheckTokenReady(false);
      setProgress({ percent: 0, stage: "cancelled" });
    } catch (error) {
      setStatus(`Cancel failed: ${sanitizeText(String(error))}`);
    }
  }

  async function handleSaveProfile(): Promise<void> {
    setBusy(true);
    try {
      const parsedGroups = parseExpectedGroups(draft.expectedGroupsJson);
      const now = new Date().toISOString();
      const profile: Profile = {
        id: draft.id,
        name: draft.name.trim() || "Unnamed profile",
        expectedGroups: parsedGroups,
        notes: draft.notes,
        createdAt: now,
        updatedAt: now,
      };
      await upsertProfile(profile);
      setDraft(freshProfileDraft());
      await refreshData();
      setStatus(`Profile '${sanitizeText(profile.name)}' saved.`);
    } catch (error) {
      setStatus(`Profile save rejected: ${sanitizeText(String(error))}`);
    } finally {
      setBusy(false);
    }
  }

  function loadProfileForEdit(profile: Profile): void {
    setDraft({
      ...profile,
      expectedGroupsJson: JSON.stringify(profile.expectedGroups, null, 2),
    });
  }

  async function handleDeleteProfile(profileId: string): Promise<void> {
    setBusy(true);
    try {
      await deleteProfile(profileId);
      await refreshData();
      setStatus("Profile deleted.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteReport(reportId: string): Promise<void> {
    setBusy(true);
    try {
      await deleteReport(reportId);
      setReports((prev) => prev.filter((entry) => entry.id !== reportId));
      if (activeReport?.id === reportId) {
        setActiveReport(null);
      }
      setStatus("Report deleted.");
    } finally {
      setBusy(false);
    }
  }

  async function handleExportBackup(): Promise<void> {
    const json = await exportBackup();
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "pinpath-backup.v1.json";
    anchor.click();
    URL.revokeObjectURL(url);
    setStatus("Backup exported.");
  }

  async function handleImportBackup(file: File | null): Promise<void> {
    if (!file) {
      return;
    }
    const text = await file.text();
    const result = await importBackup(text);
    await refreshData();
    setStatus(`Backup imported (${result.profiles} profiles, ${result.reports} reports).`);
  }

  async function handleExportCsv(): Promise<void> {
    const csv = await exportReportsCsv();
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "pinpath-reports.csv";
    anchor.click();
    URL.revokeObjectURL(url);
    setStatus("CSV report exported.");
  }

  return (
    <main>
      <h1>PinPath Companion (de-energized harness testing only)</h1>
      <p className="boundary">
        Safety boundary: this tool is for disconnected passive assemblies only. Do not use with mains, PoE, battery packs,
        energized vehicle harnesses, medical/life-safety systems, or cable certification.
      </p>

      <section aria-labelledby="connection-heading">
        <h2 id="connection-heading">USB device connection</h2>
        <div className="row">
          <button type="button" onClick={() => void handleDiscover()} disabled={busy}>
            Discover USB adapters
          </button>
          <label>
            Port
            <select value={selectedPort} onChange={(event) => setSelectedPort(event.target.value)} disabled={busy || ports.length === 0}>
              <option value="">Select</option>
              {ports.map((port) => (
                <option value={port.id} key={port.id}>
                  {port.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void handleConnect()} disabled={busy || !selectedPort}>
            Connect
          </button>
        </div>
        <p>
          {hello
            ? `Connected hardware ${hello.hardwareRevision}, firmware ${hello.firmwareVersion}, limits ${hello.limitsRevision}.`
            : "No active connection."}
        </p>
      </section>

      <section aria-labelledby="scan-heading">
        <h2 id="scan-heading">Precheck and scan workflow</h2>
        <div className="row">
          <label>
            Scan mode
            <select value={scanMode} onChange={(event) => setScanMode(event.target.value as "unknown" | "expected")} disabled={busy}>
              <option value="expected">Expected profile comparison</option>
              <option value="unknown">Unknown cable mapping</option>
            </select>
          </label>
          <label>
            Profile
            <select
              value={selectedProfileId}
              onChange={(event) => setSelectedProfileId(event.target.value)}
              disabled={scanMode !== "expected" || busy}
            >
              <option value="">Select profile</option>
              {profiles.map((profile) => (
                <option value={profile.id} key={profile.id}>
                  {profile.name}
                </option>
              ))}
            </select>
          </label>
          <button type="button" onClick={() => void handlePrecheck()} disabled={busy || !hello}>
            Run precheck
          </button>
          <button type="button" onClick={() => void handleScan()} disabled={busy || !hello}>
            Start scan
          </button>
          <button type="button" onClick={() => void handleCancel()} disabled={!hello}>
            Cancel scan
          </button>
        </div>
        <p>
          Progress: {progress.percent}% ({progress.stage})
        </p>
        <p>Precheck token status: {precheckTokenReady ? "armed" : "not armed"}</p>
      </section>

      <section aria-labelledby="profile-heading">
        <h2 id="profile-heading">Cable profiles</h2>
        <div className="grid-2">
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void handleSaveProfile();
            }}
          >
            <label>
              Profile name
              <input
                value={draft.name}
                onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
                required
              />
            </label>
            <label>
              Notes
              <input value={draft.notes} onChange={(event) => setDraft((prev) => ({ ...prev, notes: event.target.value }))} />
            </label>
            <label>
              Expected groups (JSON)
              <textarea
                rows={8}
                value={draft.expectedGroupsJson}
                onChange={(event) => setDraft((prev) => ({ ...prev, expectedGroupsJson: event.target.value }))}
              />
            </label>
            <button type="submit" disabled={busy}>
              Save profile
            </button>
          </form>

          <div>
            <h3>Saved profiles</h3>
            <ul>
              {profiles.map((profile) => (
                <li key={profile.id}>
                  <strong>{profile.name}</strong>
                  <div className="row">
                    <button type="button" onClick={() => loadProfileForEdit(profile)}>
                      Edit
                    </button>
                    <button type="button" onClick={() => void handleDeleteProfile(profile.id)}>
                      Delete
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <label>
              Import backup JSON
              <input
                type="file"
                accept="application/json"
                onChange={(event) => void handleImportBackup(event.target.files?.item(0) ?? null)}
              />
            </label>
            <div className="row">
              <button type="button" onClick={() => void handleExportBackup()}>
                Export JSON backup
              </button>
              <button type="button" onClick={() => void handleExportCsv()}>
                Export reports CSV
              </button>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="results-heading">
        <h2 id="results-heading">16×16 continuity matrix results (text and color)</h2>
        {activeReport ? (
          <>
            <p>
              Active report: {activeReport.profileName} · {activeReport.mode} · {summarize(activeReport)}
            </p>
            <div className="legend" aria-label="Result legend">
              <span>✓ match</span>
              <span>O open</span>
              <span>S short</span>
              <span>X crossover</span>
              <span>! unstable</span>
              <span>? unknown</span>
            </div>
            <div className="matrix" role="table" aria-label="PinPath continuity matrix">
              {matrix.map((cell) => (
                <div key={`${cell.row}-${cell.col}`} role="cell" className={`cell ${cell.classification}`} aria-label={cell.ariaLabel}>
                  {cell.text}
                </div>
              ))}
            </div>
          </>
        ) : (
          <p>No scan report selected.</p>
        )}

        <h3>Recent reports</h3>
        <ul>
          {reports.map((report) => (
            <li key={report.id}>
              <button type="button" onClick={() => setActiveReport(report)}>
                {new Date(report.createdAt).toLocaleString()} · {report.profileName} · {summarize(report)}
              </button>
              <button type="button" onClick={() => void handleDeleteReport(report.id)}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="status-heading">
        <h2 id="status-heading">Status and accessibility alerts</h2>
        <p role="status" aria-live="polite" className="status">
          {status}
        </p>
      </section>
    </main>
  );
}
