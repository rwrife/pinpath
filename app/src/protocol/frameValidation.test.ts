import { describe, expect, it } from "vitest";
import { validateFrame } from "./frameValidation";

describe("frame validation", () => {
  it("accepts a valid hello response", () => {
    const frame = validateFrame(
      JSON.stringify({
        v: 1,
        type: "hello_resp",
        id: "hello-123",
        payload: {
          protocolMajor: 1,
          protocolMinor: 0,
          firmwareVersion: "0.1.0",
          hardwareRevision: "rev-a",
          limitsRevision: "2026-09-01",
        },
      }),
    );

    expect(frame.type).toBe("hello_resp");
  });

  it("rejects duplicate top-level object keys", () => {
    expect(() =>
      validateFrame(
        '{"v":1,"type":"hello_resp","id":"x","payload":{},"payload":{"protocolMajor":1,"protocolMinor":0,"firmwareVersion":"0.1.0","hardwareRevision":"rev-a","limitsRevision":"2026-09-01"}}',
      ),
    ).toThrow(/duplicate object key/i);
  });

  it("rejects deeply nested payloads", () => {
    const deepPayload = {
      v: 1,
      type: "error",
      id: "deep-1",
      payload: {
        a: { b: { c: { d: { e: { f: { g: { h: { i: 1 } } } } } } } },
      },
    };
    expect(() => validateFrame(JSON.stringify(deepPayload))).toThrow(/nesting/i);
  });

  it("rejects unsupported frame types", () => {
    expect(() =>
      validateFrame(
        JSON.stringify({
          v: 1,
          type: "DROP_TABLE",
          id: "abc",
          payload: {},
        }),
      ),
    ).toThrow(/not allowed/i);
  });

  it("rejects malformed JSON frames", () => {
    expect(() => validateFrame('{"v":1,"type":"hello_resp",')).toThrow(/parse/i);
  });
});
