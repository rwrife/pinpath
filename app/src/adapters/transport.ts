import type { ValidatedFrame } from "../protocol/frameValidation";

export interface PortInfo {
  id: string;
  label: string;
}

export interface DeviceSession {
  send(frame: ValidatedFrame): Promise<ValidatedFrame>;
  pollProgress?(): Promise<ValidatedFrame[]>;
  close(): Promise<void>;
}

export interface DeviceAdapter {
  discoverPorts(): Promise<PortInfo[]>;
  connect(portId: string): Promise<DeviceSession>;
}
