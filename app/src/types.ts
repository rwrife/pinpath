export type Endpoint = `A:${string}` | `B:${string}`;

export type FaultCode =
  | "device_disconnected"
  | "precheck_stale"
  | "precheck_failed"
  | "self_test_failed"
  | "frame_invalid"
  | "protocol_incompatible"
  | "hardware_incompatible"
  | "operator_cancelled";

export interface Profile {
  id: string;
  name: string;
  expectedGroups: Endpoint[][];
  createdAt: string;
  updatedAt: string;
  notes: string;
}

export interface ScanObservation {
  observedGroups: Endpoint[][];
  unstableGroups: Endpoint[][];
  faults: FaultCode[];
}

export interface ScanComparison {
  matchedGroups: Endpoint[][];
  openGroups: Endpoint[][];
  shortGroups: Endpoint[][];
  crossoverGroups: Endpoint[][];
  unstableGroups: Endpoint[][];
  unknownGroups: Endpoint[][];
  safeToProceed: boolean;
}

export interface ScanReport {
  id: string;
  profileId: string | null;
  profileName: string;
  mode: "unknown" | "expected";
  comparison: ScanComparison;
  observation: ScanObservation;
  createdAt: string;
  hardwareRevision: string;
  firmwareVersion: string;
  limitsRevision: string;
  protocolMajor: number;
  protocolMinor: number;
  precheckPassed: boolean;
  selfTestPassed: boolean;
  notes: string;
}

export interface BackupPayload {
  schemaVersion: 1;
  exportedAt: string;
  profiles: Profile[];
  reports: ScanReport[];
}

export interface DeviceHello {
  protocolMajor: number;
  protocolMinor: number;
  firmwareVersion: string;
  hardwareRevision: string;
  limitsRevision: string;
}

export interface MatrixCell {
  row: number;
  col: number;
  classification: "pass" | "open" | "short" | "crossover" | "unstable" | "unknown";
  text: string;
  ariaLabel: string;
}
