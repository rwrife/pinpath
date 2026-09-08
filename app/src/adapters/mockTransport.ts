import type { DeviceAdapter, DeviceSession, PortInfo } from "./transport";
import type { ValidatedFrame } from "../protocol/frameValidation";

export interface MockFixture {
  id: string;
  hello: ValidatedFrame;
  precheck: ValidatedFrame;
  scanProgress: ValidatedFrame[];
  scanComplete: ValidatedFrame;
  rejectScanWithoutPrecheck?: boolean;
  disconnectOnScan?: boolean;
}

class FixtureSession implements DeviceSession {
  private precheckToken: string | null = null;
  private readonly fixture: MockFixture;

  constructor(fixture: MockFixture) {
    this.fixture = fixture;
  }

  send(frame: ValidatedFrame): Promise<ValidatedFrame> {
    switch (frame.type) {
      case "hello_req":
        return Promise.resolve(this.fixture.hello);
      case "precheck_req":
        this.precheckToken = String(this.fixture.precheck.payload.token ?? "token-ok");
        return Promise.resolve(this.fixture.precheck);
      case "scan_req": {
        if (this.fixture.disconnectOnScan) {
          throw new Error("device_disconnected");
        }
        const requestedToken = String(frame.payload.precheckToken ?? "");
        if (this.fixture.rejectScanWithoutPrecheck && requestedToken !== this.precheckToken) {
          return Promise.resolve({
            v: 1,
            type: "error",
            id: frame.id,
            payload: {
              code: "precheck_stale",
              message: "scan rejected because precheck token is stale",
            },
          });
        }
        return Promise.resolve(this.fixture.scanComplete);
      }
      case "scan_cancel_req":
        return Promise.resolve({
          v: 1,
          type: "error",
          id: frame.id,
          payload: {
            code: "operator_cancelled",
            message: "scan cancelled",
          },
        });
      default:
        return Promise.resolve({
          v: 1,
          type: "error",
          id: frame.id,
          payload: {
            code: "unsupported",
            message: `mock does not implement ${frame.type}`,
          },
        });
    }
  }

  pollProgress(): Promise<ValidatedFrame[]> {
    return Promise.resolve(this.fixture.scanProgress);
  }

  close(): Promise<void> {
    return Promise.resolve();
  }
}

export class MockAdapter implements DeviceAdapter {
  private readonly fixtures: MockFixture[];

  constructor(fixtures: MockFixture[]) {
    this.fixtures = fixtures;
  }

  discoverPorts(): Promise<PortInfo[]> {
    return Promise.resolve(this.fixtures.map((fixture, index) => ({
      id: fixture.id,
      label: `Mock Device ${index + 1} (${fixture.id})`,
    })));
  }

  connect(portId: string): Promise<DeviceSession> {
    const fixture = this.fixtures.find((entry) => entry.id === portId);
    if (!fixture) {
      throw new Error(`mock fixture '${portId}' not found`);
    }
    return Promise.resolve(new FixtureSession(fixture));
  }
}
