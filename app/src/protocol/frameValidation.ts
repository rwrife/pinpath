import { parseTree, printParseErrorCode, type Node, type ParseError } from "jsonc-parser";
import { z } from "zod";

const ALLOWED_TYPES = new Set([
  "hello_req",
  "hello_resp",
  "precheck_req",
  "precheck_resp",
  "scan_req",
  "scan_progress",
  "scan_complete",
  "scan_cancel_req",
  "error",
]);

const MAX_FRAME_BYTES = 32768;
const MAX_DEPTH = 8;
const MAX_STRING_BYTES = 1024;
const MAX_ARRAY_LENGTH = 1024;

const EndpointSchema = z.string().regex(/^[AB]:\d{2}$/);
const EndpointGroupSchema = z.array(EndpointSchema).min(1).max(32);

const HelloRespPayloadSchema = z.object({
  protocolMajor: z.number().int().nonnegative(),
  protocolMinor: z.number().int().nonnegative(),
  firmwareVersion: z.string().min(1).max(128),
  hardwareRevision: z.string().min(1).max(64),
  limitsRevision: z.string().min(1).max(64),
});

const ScanCompletePayloadSchema = z.object({
  observedGroups: z.array(EndpointGroupSchema).max(512),
  unstableGroups: z.array(EndpointGroupSchema).max(512).optional().default([]),
  faults: z.array(z.string().max(64)).max(32).optional().default([]),
});

const ScanProgressPayloadSchema = z.object({
  percent: z.number().int().min(0).max(100),
  stage: z.string().max(128),
});

const ErrorPayloadSchema = z.object({
  code: z.string().max(64),
  message: z.string().max(512),
});

const PrecheckRespPayloadSchema = z.object({
  pass: z.boolean(),
  token: z.string().max(128).optional(),
  detail: z.string().max(256).optional(),
});

const ScanReqPayloadSchema = z.object({
  mode: z.enum(["unknown", "expected"]),
  profileId: z.string().max(64).optional(),
  precheckToken: z.string().max(128),
});

const AnyPayloadSchema = z.record(z.string(), z.unknown());

const FrameSchema = z.object({
  v: z.number().int().min(1).max(1),
  type: z.string().min(1).max(64),
  id: z.string().regex(/^[A-Za-z0-9._:-]{1,64}$/),
  payload: AnyPayloadSchema,
});

export interface ValidatedFrame {
  v: 1;
  type: string;
  id: string;
  payload: Record<string, unknown>;
}

function utf8Len(input: string): number {
  return new TextEncoder().encode(input).length;
}

function walkNode(node: Node, depth: number): void {
  if (depth > MAX_DEPTH) {
    throw new Error(`frame nesting exceeds ${MAX_DEPTH}`);
  }

  if (node.type === "string" && typeof node.value === "string" && utf8Len(node.value) > MAX_STRING_BYTES) {
    throw new Error(`string literal exceeds ${MAX_STRING_BYTES} UTF-8 bytes`);
  }

  if (node.type === "array" && Array.isArray(node.children) && node.children.length > MAX_ARRAY_LENGTH) {
    throw new Error(`array length exceeds ${MAX_ARRAY_LENGTH}`);
  }

  if (node.type === "object" && Array.isArray(node.children)) {
    const keySet = new Set<string>();
    for (const child of node.children) {
      if (child.type !== "property" || !Array.isArray(child.children) || child.children.length < 2) {
        continue;
      }
      const keyNode = child.children[0];
      if (typeof keyNode.value !== "string") {
        continue;
      }
      if (keySet.has(keyNode.value)) {
        throw new Error(`duplicate object key '${keyNode.value}'`);
      }
      keySet.add(keyNode.value);
    }
  }

  if (!Array.isArray(node.children)) {
    return;
  }
  for (const child of node.children) {
    walkNode(child, depth + 1);
  }
}

function validatePayloadByType(type: string, payload: Record<string, unknown>): void {
  switch (type) {
    case "hello_resp":
      void HelloRespPayloadSchema.parse(payload);
      return;
    case "scan_complete":
      void ScanCompletePayloadSchema.parse(payload);
      return;
    case "scan_progress":
      void ScanProgressPayloadSchema.parse(payload);
      return;
    case "error":
      void ErrorPayloadSchema.parse(payload);
      return;
    case "precheck_resp":
      void PrecheckRespPayloadSchema.parse(payload);
      return;
    case "scan_req":
      void ScanReqPayloadSchema.parse(payload);
      return;
    default:
      return;
  }
}

export function sanitizeText(value: unknown): string {
  const rawMaybe = typeof value === "string" ? value : JSON.stringify(value);
  const raw = typeof rawMaybe === "string" ? rawMaybe : String(value ?? "");
  const safe = Array.from(raw)
    .map((ch) => {
      const code = ch.charCodeAt(0);
      if (code <= 0x1f || code === 0x7f || ch === "<" || ch === ">") {
        return " ";
      }
      return ch;
    })
    .join("");
  return safe.slice(0, 512);
}

export function validateFrame(rawFrame: string): ValidatedFrame {
  if (utf8Len(rawFrame) > MAX_FRAME_BYTES) {
    throw new Error(`frame exceeds ${MAX_FRAME_BYTES} UTF-8 bytes`);
  }

  const errors: ParseError[] = [];
  const tree = parseTree(rawFrame, errors, { disallowComments: true, allowTrailingComma: false });
  if (!tree) {
    throw new Error("frame is not parseable JSON");
  }
  if (errors.length > 0) {
    const reason = printParseErrorCode(errors[0].error);
    throw new Error(`JSON parse error: ${reason}`);
  }

  walkNode(tree, 0);

  const parsed: unknown = JSON.parse(rawFrame);
  const frame = FrameSchema.parse(parsed);
  if (!ALLOWED_TYPES.has(frame.type)) {
    throw new Error(`frame type '${frame.type}' is not allowed`);
  }

  validatePayloadByType(frame.type, frame.payload);

  return {
    v: 1,
    type: frame.type,
    id: frame.id,
    payload: frame.payload,
  };
}
