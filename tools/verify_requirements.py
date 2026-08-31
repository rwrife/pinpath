#!/usr/bin/env python3
"""Validate PinPath requirement traceability and critical safety language."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "hardware" / "requirements.md"
MATRIX = ROOT / "docs" / "verification-matrix.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
RISK = ROOT / "docs" / "risk-analysis.md"
PROTOCOL = ROOT / "docs" / "protocol.md"
README = ROOT / "README.md"

REQ_HEADING = re.compile(r"^### (REQ-[A-Z]+-\d{3}) — .+$", re.MULTILINE)
MATRIX_ROW = re.compile(r"^\| (REQ-[A-Z]+-\d{3}) \|", re.MULTILINE)
RELATIVE_LINK = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)#]+)(?:#[^)]+)?\)")


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def validate_requirement_blocks(text: str, ids: list[str]) -> None:
    positions = [text.index(f"### {req_id}") for req_id in ids] + [len(text)]
    for index, req_id in enumerate(ids):
        block = text[positions[index] : positions[index + 1]]
        for marker in ("**Requirement.**", "**Rationale.**", "**Planned verification.**"):
            if marker not in block:
                fail(f"{req_id} is missing {marker}")
        normative = block.split("**Rationale.**", 1)[0]
        if " shall " not in normative and " shall not " not in normative:
            fail(f"{req_id} has no normative shall/shall-not statement")


def validate_links(paths: list[Path]) -> int:
    count = 0
    for path in paths:
        text = read(path)
        for match in RELATIVE_LINK.finditer(text):
            target = (path.parent / match.group(1)).resolve()
            try:
                target.relative_to(ROOT)
            except ValueError:
                fail(f"link escapes repository in {path.relative_to(ROOT)}: {match.group(1)}")
            if not target.exists():
                fail(f"broken relative link in {path.relative_to(ROOT)}: {match.group(1)}")
            count += 1
    return count


def main() -> int:
    req_text = read(REQUIREMENTS)
    matrix_text = read(MATRIX)
    req_ids = REQ_HEADING.findall(req_text)
    matrix_ids = MATRIX_ROW.findall(matrix_text)

    if not req_ids:
        fail("no requirement headings found")
    if duplicate := duplicates(req_ids):
        fail(f"duplicate requirement IDs: {', '.join(duplicate)}")
    if duplicate := duplicates(matrix_ids):
        fail(f"duplicate matrix IDs: {', '.join(duplicate)}")

    missing = sorted(set(req_ids) - set(matrix_ids))
    unknown = sorted(set(matrix_ids) - set(req_ids))
    if missing:
        fail(f"requirements missing from matrix: {', '.join(missing)}")
    if unknown:
        fail(f"matrix references unknown requirements: {', '.join(unknown)}")

    validate_requirement_blocks(req_text, req_ids)

    required_boundary_terms = (
        "de-energized",
        "mains",
        "poe",
        "battery",
        "powered usb",
        "vehicle",
        "medical",
        "life-safety",
        "cable certification",
    )
    boundary_documents = (
        README,
        REQUIREMENTS,
        ARCHITECTURE,
        RISK,
        PROTOCOL,
        ROOT / "hardware" / "README.md",
        ROOT / "firmware" / "README.md",
        ROOT / "app" / "README.md",
    )
    for document in boundary_documents:
        text = read(document).lower()
        absent = [term for term in required_boundary_terms if term not in text]
        if absent:
            fail(
                f"{document.relative_to(ROOT)} is missing safety-boundary terms: "
                f"{', '.join(absent)}"
            )

    architecture_text = read(ARCHITECTURE)
    for endpoint in ("A:01", "A:16", "B:01", "B:16"):
        if endpoint not in architecture_text:
            fail(f"architecture omits canonical endpoint boundary {endpoint}")

    consistency_fragments = {
        REQUIREMENTS: (
            "if received while `armed`, it shall invalidate the precheck token",
            "a complete bijective two-endpoint `crossover` is evaluated before `short`",
        ),
        ARCHITECTURE: (
            "if armed, invalidate the token and leave `ARMED`",
            "complete stable bijection of two-endpoint observed groups",
        ),
        PROTOCOL: (
            "Any rejected input while `armed` also invalidates the token and leaves `armed`",
        ),
    }
    for document, fragments in consistency_fragments.items():
        text = read(document)
        for fragment in fragments:
            if fragment not in text:
                fail(
                    f"{document.relative_to(ROOT)} is missing cross-document invariant: "
                    f"{fragment}"
                )

    forbidden_contradictions = (
        "`short` takes precedence over `crossover`",
        "without consuming a precheck token",
    )
    normative_text = "\n".join(read(path) for path in (REQUIREMENTS, ARCHITECTURE, PROTOCOL))
    for contradiction in forbidden_contradictions:
        if contradiction in normative_text:
            fail(f"normative documents retain contradictory rule: {contradiction}")

    risk_text = read(RISK)
    risk_ids = re.findall(r"^\| (RISK-\d{3}) \|", risk_text, re.MULTILINE)
    if len(risk_ids) < 20 or duplicates(risk_ids):
        fail("risk table must contain at least 20 unique identified misuse/fault cases")

    files = list(boundary_documents) + [MATRIX]
    link_count = validate_links(files)

    print(f"PASS requirements={len(req_ids)} matrix_rows={len(matrix_ids)} risks={len(risk_ids)} relative_links={link_count}")
    print("PASS requirement IDs are unique and fully traced")
    print("PASS every requirement has statement, rationale, and planned verification")
    print("PASS per-document safety boundaries, canonical endpoints, risk coverage, and relative links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
