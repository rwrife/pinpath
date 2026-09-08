import type { MockFixture } from "../adapters/mockTransport";

export const DEFAULT_FIXTURES: MockFixture[] = [
  {
    id: "fixture-pass",
    hello: {
      v: 1,
      type: "hello_resp",
      id: "hello-1",
      payload: {
        protocolMajor: 1,
        protocolMinor: 0,
        firmwareVersion: "0.1.0",
        hardwareRevision: "rev-a",
        limitsRevision: "2026-09-01",
      },
    },
    precheck: {
      v: 1,
      type: "precheck_resp",
      id: "precheck-1",
      payload: { pass: true, token: "token-pass" },
    },
    scanProgress: [
      { v: 1, type: "scan_progress", id: "scan-p1", payload: { percent: 25, stage: "stabilizing" } },
      { v: 1, type: "scan_progress", id: "scan-p2", payload: { percent: 75, stage: "mapping" } },
    ],
    scanComplete: {
      v: 1,
      type: "scan_complete",
      id: "scan-done",
      payload: {
        observedGroups: [["A:01", "B:01"], ["A:02", "B:02"]],
        unstableGroups: [],
        faults: [],
      },
    },
    rejectScanWithoutPrecheck: true,
  },
  {
    id: "fixture-open",
    hello: {
      v: 1,
      type: "hello_resp",
      id: "hello-open",
      payload: {
        protocolMajor: 1,
        protocolMinor: 0,
        firmwareVersion: "0.1.0",
        hardwareRevision: "rev-a",
        limitsRevision: "2026-09-01",
      },
    },
    precheck: {
      v: 1,
      type: "precheck_resp",
      id: "precheck-open",
      payload: { pass: true, token: "token-open" },
    },
    scanProgress: [{ v: 1, type: "scan_progress", id: "scan-open", payload: { percent: 60, stage: "mapping" } }],
    scanComplete: {
      v: 1,
      type: "scan_complete",
      id: "scan-open-done",
      payload: {
        observedGroups: [["A:01", "B:01"]],
        unstableGroups: [],
        faults: [],
      },
    },
    rejectScanWithoutPrecheck: true,
  },
  {
    id: "fixture-faulty",
    hello: {
      v: 1,
      type: "hello_resp",
      id: "hello-2",
      payload: {
        protocolMajor: 1,
        protocolMinor: 0,
        firmwareVersion: "0.1.0",
        hardwareRevision: "rev-a",
        limitsRevision: "2026-09-01",
      },
    },
    precheck: {
      v: 1,
      type: "precheck_resp",
      id: "precheck-2",
      payload: { pass: true, token: "token-faulty" },
    },
    scanProgress: [{ v: 1, type: "scan_progress", id: "scan-p3", payload: { percent: 50, stage: "mapping" } }],
    scanComplete: {
      v: 1,
      type: "scan_complete",
      id: "scan-done-2",
      payload: {
        observedGroups: [["A:01", "B:02"], ["A:02", "B:01", "B:03"]],
        unstableGroups: [["A:03", "B:04"]],
        faults: ["self_test_failed"],
      },
    },
    rejectScanWithoutPrecheck: true,
  },
  {
    id: "fixture-disconnect",
    hello: {
      v: 1,
      type: "hello_resp",
      id: "hello-disconnect",
      payload: {
        protocolMajor: 1,
        protocolMinor: 0,
        firmwareVersion: "0.1.0",
        hardwareRevision: "rev-a",
        limitsRevision: "2026-09-01",
      },
    },
    precheck: {
      v: 1,
      type: "precheck_resp",
      id: "precheck-disconnect",
      payload: { pass: true, token: "token-disconnect" },
    },
    scanProgress: [{ v: 1, type: "scan_progress", id: "scan-disc", payload: { percent: 15, stage: "mapping" } }],
    scanComplete: {
      v: 1,
      type: "scan_complete",
      id: "scan-disconnect-unused",
      payload: {
        observedGroups: [],
        unstableGroups: [],
        faults: ["device_disconnected"],
      },
    },
    rejectScanWithoutPrecheck: true,
    disconnectOnScan: true,
  },
  {
    id: "fixture-incompatible",
    hello: {
      v: 1,
      type: "hello_resp",
      id: "hello-3",
      payload: {
        protocolMajor: 2,
        protocolMinor: 0,
        firmwareVersion: "0.2.0",
        hardwareRevision: "rev-z",
        limitsRevision: "2026-09-01",
      },
    },
    precheck: {
      v: 1,
      type: "precheck_resp",
      id: "precheck-3",
      payload: { pass: true, token: "token-incompatible" },
    },
    scanProgress: [],
    scanComplete: {
      v: 1,
      type: "scan_complete",
      id: "scan-done-3",
      payload: {
        observedGroups: [],
        unstableGroups: [],
        faults: ["protocol_incompatible"],
      },
    },
    rejectScanWithoutPrecheck: true,
  },
];
