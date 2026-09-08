import type { DeviceAdapter, DeviceSession, PortInfo } from "../adapters/transport";
import { compareObservedToExpected, parseObservedGroups } from "../logic/comparison";
import { sanitizeText, validateFrame } from "./frameValidation";
import type {
  DeviceHello,
  FaultCode,
  Profile,
  ScanComparison,
  ScanObservation,
  ScanReport,
} from "../types";

function requestId(prefix: string): string {
  const stamp = Math.trunc(performance.now()).toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${stamp}-${rand}`;
}

export interface ScanProgress {
  percent: number;
  stage: string;
}

export class ProtocolClient {
  private readonly adapter: DeviceAdapter;
  private session: DeviceSession | null = null;
  private hello: DeviceHello | null = null;
  private pendingPrecheckToken: string | null = null;

  constructor(adapter: DeviceAdapter) {
    this.adapter = adapter;
  }

  async discover(): Promise<PortInfo[]> {
    return this.adapter.discoverPorts();
  }

  async connect(portId: string): Promise<DeviceHello> {
    this.session = await this.adapter.connect(portId);
    const helloResponseRaw = await this.session.send({
      v: 1,
      type: "hello_req",
      id: requestId("hello"),
      payload: {},
    });
    const helloResponse = validateFrame(JSON.stringify(helloResponseRaw));
    if (helloResponse.type !== "hello_resp") {
      throw new Error(`expected hello_resp, got ${sanitizeText(helloResponse.type)}`);
    }

    const payload = helloResponse.payload;
    const details: DeviceHello = {
      protocolMajor: Number(payload.protocolMajor),
      protocolMinor: Number(payload.protocolMinor),
      firmwareVersion: String(payload.firmwareVersion ?? "unknown"),
      hardwareRevision: String(payload.hardwareRevision ?? "unknown"),
      limitsRevision: String(payload.limitsRevision ?? "unknown"),
    };

    if (details.protocolMajor !== 1) {
      this.pendingPrecheckToken = null;
      throw new Error(
        `protocol incompatibility: expected protocol major 1, received ${details.protocolMajor}`,
      );
    }
    if (details.hardwareRevision.toLowerCase() !== "rev-a") {
      this.pendingPrecheckToken = null;
      throw new Error(
        `hardware incompatibility: expected rev-a, received ${details.hardwareRevision}`,
      );
    }

    this.hello = details;
    return details;
  }

  async disconnect(): Promise<void> {
    if (this.session) {
      await this.session.close();
    }
    this.session = null;
    this.hello = null;
    this.pendingPrecheckToken = null;
  }

  async runPrecheck(): Promise<{ pass: boolean; token: string | null; detail: string }> {
    if (!this.session) {
      throw new Error("device is not connected");
    }
    const responseRaw = await this.session.send({
      v: 1,
      type: "precheck_req",
      id: requestId("precheck"),
      payload: {},
    });
    const response = validateFrame(JSON.stringify(responseRaw));
    if (response.type !== "precheck_resp") {
      throw new Error(`expected precheck_resp, got ${sanitizeText(response.type)}`);
    }
    const pass = Boolean(response.payload.pass);
    const token = typeof response.payload.token === "string" ? response.payload.token : null;
    const detail = typeof response.payload.detail === "string" ? response.payload.detail : "";
    this.pendingPrecheckToken = pass ? token : null;
    return { pass, token, detail };
  }

  async runScan(
    mode: "unknown" | "expected",
    profile: Profile | null,
    onProgress: (progress: ScanProgress) => void,
  ): Promise<ScanReport> {
    if (!this.session || !this.hello) {
      throw new Error("device must be connected before scanning");
    }
    if (!this.pendingPrecheckToken) {
      throw new Error("precheck token missing; run precheck immediately before scan");
    }

    const progressFrames = await this.session.pollProgress?.();
    for (const frameRaw of progressFrames ?? []) {
      const frame = validateFrame(JSON.stringify(frameRaw));
      if (frame.type === "scan_progress") {
        onProgress({
          percent: Number(frame.payload.percent ?? 0),
          stage: String(frame.payload.stage ?? "working"),
        });
      }
    }

    const responseRaw = await this.session.send({
      v: 1,
      type: "scan_req",
      id: requestId("scan"),
      payload: {
        mode,
        profileId: profile?.id,
        precheckToken: this.pendingPrecheckToken,
      },
    });
    const response = validateFrame(JSON.stringify(responseRaw));

    this.pendingPrecheckToken = null;

    if (response.type === "error") {
      const message = String(response.payload.message ?? response.payload.code ?? "scan failed");
      throw new Error(sanitizeText(message));
    }
    if (response.type !== "scan_complete") {
      throw new Error(`expected scan_complete, got ${sanitizeText(response.type)}`);
    }

    onProgress({ percent: 100, stage: "complete" });

    const observedGroups = parseObservedGroups(response.payload.observedGroups);
    const unstableGroups = parseObservedGroups(response.payload.unstableGroups ?? []);
    const faults = Array.isArray(response.payload.faults)
      ? response.payload.faults.filter((entry): entry is FaultCode => typeof entry === "string")
      : [];

    const observation: ScanObservation = {
      observedGroups,
      unstableGroups,
      faults,
    };

    const comparison: ScanComparison = compareObservedToExpected(profile?.expectedGroups ?? [], observation);

    return {
      id: crypto.randomUUID(),
      profileId: profile?.id ?? null,
      profileName: profile?.name ?? "Unknown cable",
      mode,
      comparison,
      observation,
      createdAt: new Date().toISOString(),
      hardwareRevision: this.hello.hardwareRevision,
      firmwareVersion: this.hello.firmwareVersion,
      limitsRevision: this.hello.limitsRevision,
      protocolMajor: this.hello.protocolMajor,
      protocolMinor: this.hello.protocolMinor,
      precheckPassed: true,
      selfTestPassed: !faults.includes("self_test_failed"),
      notes: "",
    };
  }

  async cancelScan(): Promise<void> {
    if (!this.session) {
      return;
    }
    await this.session.send({
      v: 1,
      type: "scan_cancel_req",
      id: requestId("cancel"),
      payload: {},
    });
    this.pendingPrecheckToken = null;
  }
}
