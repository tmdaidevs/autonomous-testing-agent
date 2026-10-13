from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .io_utils import utc_now, write_json


CHECKBOX_PATTERN = re.compile(
    r"^\s*[-*]\s+\[(?: |x|X)\]\s+"
    r"(?:(?P<id>[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)"
    r"\s*[-:]\s*)?(?P<title>.+?)\s*$"
)
HEADING_PATTERN = re.compile(
    r"^#{2,6}\s+"
    r"(?P<id>[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+)"
    r"(?:\s*[-:]\s*|\s+)(?P<title>.+?)\s*$"
)


def extract_plan(source: Path) -> dict[str, Any]:
    text = source.read_text(encoding="utf-8")
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    generated = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = CHECKBOX_PATTERN.match(line) or HEADING_PATTERN.match(line)
        if not match:
            continue
        check_id = match.groupdict().get("id")
        if check_id:
            check_id = check_id.upper()
        else:
            generated += 1
            check_id = f"CHECK-{generated:03d}"
        if check_id in seen:
            continue
        seen.add(check_id)
        cases.append(
            {
                "id": check_id,
                "title": match.group("title").strip(),
                "status": "not_tested",
                "source_line": line_number,
                "dependencies": [],
                "finding_ids": [],
                "evidence_ids": [],
                "attempts": [],
            }
        )

    return {
        "schema_version": 1,
        "source": str(source),
        "created_at": utc_now(),
        "requires_review": True,
        "test_cases": cases,
    }


def write_plan(source: Path, output: Path) -> dict[str, Any]:
    plan = extract_plan(source)
    write_json(output, plan)
    return plan
