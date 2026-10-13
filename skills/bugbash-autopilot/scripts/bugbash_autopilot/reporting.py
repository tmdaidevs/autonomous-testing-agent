from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Any

from .evidence import MANIFEST_PATH, RESULTS_PATH
from .io_utils import read_json, utc_now


def _cell(value: object) -> str:
    if value is None:
        return ""
    return str(value).replace("|", r"\|").replace("\n", "<br>")


def _display(value: object) -> str:
    return str(value or "").replace("_", " ").title()


def _image_target(run_dir: Path, output: Path, relative_path: str) -> str:
    absolute = (run_dir / relative_path).resolve()
    relative = os.path.relpath(absolute, output.parent.resolve())
    return Path(relative).as_posix()


def generate_report(run_dir: Path, output: Path) -> str:
    results = read_json(run_dir / RESULTS_PATH)
    manifest = read_json(run_dir / MANIFEST_PATH)
    run = results.get("run", {})
    cases = results.get("test_cases", [])
    findings = results.get("findings", [])
    submissions = results.get("submissions", [])
    evidence = manifest.get("evidence", [])
    evidence_by_id = {
        item.get("evidence_id"): item
        for item in evidence
        if item.get("evidence_id")
    }

    status_counts = Counter(case.get("status") for case in cases)
    severity_counts = Counter(
        finding.get("severity") for finding in findings
    )
    lines = [
        f"# {_cell(run.get('title') or 'Bug Bash Report')}",
        "",
        "## Test context",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run ID | `{_cell(run.get('id'))}` |",
        f"| Source document | `{_cell(run.get('source_document'))}` |",
        f"| Target | {_cell(run.get('target_url'))} |",
        f"| Created | {_cell(run.get('created_at'))} |",
        f"| Report generated | {utc_now()} |",
        "",
        "## Summary",
        "",
        f"- **Test cases:** {len(cases)}",
        f"- **Confirmed findings:** {len(findings)}",
        f"- **Evidence items:** {len(evidence)}",
        f"- **External submissions:** {len(submissions)}",
    ]
    if status_counts:
        status_summary = ", ".join(
            f"{_display(status)}: {count}"
            for status, count in sorted(status_counts.items())
        )
        lines.append(f"- **Case results:** {status_summary}")
    if severity_counts:
        severity_summary = ", ".join(
            f"{_display(severity)}: {count}"
            for severity, count in sorted(severity_counts.items())
        )
        lines.append(f"- **Severity:** {severity_summary}")

    lines.extend(
        [
            "",
            "## Test execution",
            "",
            "| Check | Status | Expected | Actual | Evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for case in cases:
        evidence_links = ", ".join(
            f"`{evidence_id}`" for evidence_id in case.get("evidence_ids", [])
        )
        if not evidence_links and case.get("evidence_exception"):
            evidence_links = f"Exception: {_cell(case['evidence_exception'])}"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(case.get('id'))}` - {_cell(case.get('title'))}",
                    _display(case.get("status")),
                    _cell(case.get("expected")),
                    _cell(case.get("actual")),
                    evidence_links,
                ]
            )
            + " |"
        )

    lines.extend(["", "## Confirmed findings", ""])
    if not findings:
        lines.extend(["No confirmed findings.", ""])
    for finding in findings:
        finding_id = finding.get("id", "UNKNOWN")
        lines.extend(
            [
                f"### {_cell(finding_id)} - {_cell(finding.get('title'))}",
                "",
                f"- **Severity:** {_display(finding.get('severity'))}",
                f"- **Area:** {_cell(finding.get('area'))}",
                "- **Affected checks:** "
                + ", ".join(
                    f"`{_cell(case_id)}`"
                    for case_id in finding.get("test_case_ids", [])
                ),
                "",
                "**Reproduction**",
                "",
            ]
        )
        for index, step in enumerate(finding.get("steps", []), start=1):
            lines.append(f"{index}. {_cell(step)}")
        lines.extend(
            [
                "",
                f"**Expected:** {_cell(finding.get('expected'))}",
                "",
                f"**Actual:** {_cell(finding.get('actual'))}",
                "",
                f"**Impact:** {_cell(finding.get('impact'))}",
            ]
        )
        recommendation = finding.get("recommendation")
        if recommendation:
            lines.extend(
                ["", f"**Recommendation:** {_cell(recommendation)}"]
            )
        tracking_ids = finding.get("external_tracking_ids", [])
        if tracking_ids:
            lines.extend(
                [
                    "",
                    "**External tracking:** "
                    + ", ".join(f"`{_cell(item)}`" for item in tracking_ids),
                ]
            )

        finding_evidence = finding.get("evidence_ids", [])
        if finding_evidence:
            lines.extend(["", "**Evidence**", ""])
            for evidence_id in finding_evidence:
                entry = evidence_by_id.get(evidence_id)
                if not entry:
                    lines.append(f"- Missing manifest entry `{evidence_id}`")
                    continue
                target = _image_target(run_dir, output, entry["path"])
                lines.extend(
                    [
                        f"![{_cell(entry.get('description'))}]({target})",
                        "",
                        f"`{_cell(evidence_id)}` - "
                        f"{_cell(entry.get('description'))}",
                        "",
                    ]
                )
        elif finding.get("evidence_exception"):
            lines.extend(
                [
                    "",
                    "**Evidence exception:** "
                    + _cell(finding.get("evidence_exception")),
                    "",
                ]
            )

    lines.extend(
        [
            "## Submission log",
            "",
            "| Tracking ID | Check IDs | Finding IDs | Status |",
            "|---|---|---|---|",
        ]
    )
    for submission in submissions:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(submission.get('tracking_id'))}`",
                    ", ".join(
                        f"`{_cell(item)}`"
                        for item in submission.get("test_case_ids", [])
                    ),
                    ", ".join(
                        f"`{_cell(item)}`"
                        for item in submission.get("finding_ids", [])
                    ),
                    _cell(submission.get("status")),
                ]
            )
            + " |"
        )
    if not submissions:
        lines.append("| None |  |  |  |")

    lines.extend(
        [
            "",
            "## Evidence index",
            "",
            "| Evidence | Check | Finding | Description | Attachment | Tracking ID |",
            "|---|---|---|---|---|---|",
        ]
    )
    for entry in evidence:
        attachment = entry.get("attachment", {})
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{_cell(entry.get('evidence_id'))}`",
                    f"`{_cell(entry.get('test_case_id'))}`",
                    f"`{_cell(entry.get('finding_id'))}`"
                    if entry.get("finding_id")
                    else "",
                    _cell(entry.get("description")),
                    _display(attachment.get("status")),
                    f"`{_cell(attachment.get('external_tracking_id'))}`"
                    if attachment.get("external_tracking_id")
                    else "",
                ]
            )
            + " |"
        )
    lines.append("")

    content = "\n".join(lines)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8", newline="\n")
    return content
