from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

from PIL import Image, UnidentifiedImageError

from .evidence import ATTACHMENT_STATUSES, MANIFEST_PATH, RESULTS_PATH
from .io_utils import read_json, resolve_run_path, sha256_file


CASE_STATUSES = {
    "works",
    "works_with_issue",
    "issue",
    "blocked",
    "not_tested",
    "skipped",
}
SEVERITIES = {"critical", "high", "medium", "low"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
IMAGE_LINK_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class ValidationMessage:
    code: str
    message: str


@dataclass
class ValidationReport:
    errors: list[ValidationMessage] = field(default_factory=list)
    warnings: list[ValidationMessage] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str) -> None:
        self.errors.append(ValidationMessage(code, message))

    def warning(self, code: str, message: str) -> None:
        self.warnings.append(ValidationMessage(code, message))


def _require_list(
    value: object,
    name: str,
    report: ValidationReport,
) -> list[dict]:
    if not isinstance(value, list):
        report.error("invalid-type", f"{name} must be an array")
        return []
    invalid = [item for item in value if not isinstance(item, dict)]
    if invalid:
        report.error(
            "invalid-type",
            f"{name} must contain only JSON objects",
        )
        return [item for item in value if isinstance(item, dict)]
    return value


def _duplicate_values(items: list[dict], key: str) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _validate_evidence_file(
    run_dir: Path,
    relative_path: object,
    expected_hash: object,
    label: str,
    report: ValidationReport,
) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        report.error("missing-path", f"{label} path is missing")
        return None
    try:
        path = resolve_run_path(run_dir, relative_path)
    except ValueError as error:
        report.error("unsafe-path", str(error))
        return None
    if not path.is_file():
        report.error("missing-file", f"{label} does not exist: {relative_path}")
        return path
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        report.error(
            "missing-hash",
            f"{label} has no valid SHA-256 value: {relative_path}",
        )
    else:
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            report.error(
                "hash-mismatch",
                f"{label} hash mismatch: {relative_path}",
            )
    try:
        with Image.open(path) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        report.error(
            "invalid-image",
            f"{label} is not a valid image: {relative_path} ({error})",
        )
    return path


def _validate_markdown_links(
    run_dir: Path,
    report: ValidationReport,
) -> None:
    for markdown_path in run_dir.glob("*.md"):
        content = markdown_path.read_text(encoding="utf-8")
        for raw_target in IMAGE_LINK_PATTERN.findall(content):
            target = raw_target.strip().strip("<>")
            if target.startswith(("http://", "https://", "data:", "#")):
                continue
            if ' "' in target:
                target = target.split(' "', 1)[0]
            resolved = (markdown_path.parent / unquote(target)).resolve()
            try:
                resolved.relative_to(run_dir.resolve())
            except ValueError:
                report.error(
                    "unsafe-markdown-link",
                    f"{markdown_path.name} links outside the run: {target}",
                )
                continue
            if not resolved.is_file():
                report.error(
                    "broken-markdown-link",
                    f"{markdown_path.name} references missing image: {target}",
                )


def validate_run(run_dir: Path) -> ValidationReport:
    report = ValidationReport()
    results_path = run_dir / RESULTS_PATH
    manifest_path = run_dir / MANIFEST_PATH

    if not results_path.is_file():
        report.error("missing-results", f"Missing {RESULTS_PATH}")
    if not manifest_path.is_file():
        report.error("missing-manifest", f"Missing {MANIFEST_PATH}")
    if report.errors:
        return report

    results = read_json(results_path)
    manifest = read_json(manifest_path)
    run = results.get("run")
    if not isinstance(run, dict):
        report.error("invalid-run", "results.json must contain a run object")
        run = {}
    run_id = run.get("id")
    if not isinstance(run_id, str) or not run_id:
        report.error("missing-run-id", "results.json run.id is required")
    if manifest.get("run_id") != run_id:
        report.error(
            "run-id-mismatch",
            "results.json and evidence/manifest.json use different run IDs",
        )

    policy = manifest.get("policy")
    if not isinstance(policy, dict):
        report.error("invalid-policy", "Manifest policy must be an object")
        policy = {}
    max_bytes = policy.get("max_attachment_bytes")
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        report.error(
            "invalid-policy",
            "policy.max_attachment_bytes must be a positive integer",
        )
        max_bytes = 2 * 1024 * 1024
    if policy.get("preserve_originals") is not True:
        report.error(
            "invalid-policy",
            "policy.preserve_originals must be true",
        )

    evidence = _require_list(
        manifest.get("evidence"),
        "manifest.evidence",
        report,
    )
    cases = _require_list(
        results.get("test_cases"),
        "results.test_cases",
        report,
    )
    findings = _require_list(
        results.get("findings"),
        "results.findings",
        report,
    )
    submissions = _require_list(
        results.get("submissions"),
        "results.submissions",
        report,
    )

    for collection_name, collection, key in (
        ("evidence", evidence, "evidence_id"),
        ("test case", cases, "id"),
        ("finding", findings, "id"),
        ("submission", submissions, "tracking_id"),
    ):
        for duplicate in sorted(_duplicate_values(collection, key)):
            report.error(
                "duplicate-id",
                f"Duplicate {collection_name} {key}: {duplicate}",
            )

    evidence_ids = {
        item.get("evidence_id")
        for item in evidence
        if isinstance(item.get("evidence_id"), str)
    }
    case_ids = {
        item.get("id")
        for item in cases
        if isinstance(item.get("id"), str)
    }
    finding_ids = {
        item.get("id")
        for item in findings
        if isinstance(item.get("id"), str)
    }
    referenced_image_paths: set[Path] = set()

    for entry in evidence:
        evidence_id = entry.get("evidence_id")
        label = (
            f"Evidence {evidence_id}"
            if isinstance(evidence_id, str)
            else "Evidence with missing ID"
        )
        if not isinstance(evidence_id, str) or not re.fullmatch(
            r"EVD-\d{3,}", evidence_id
        ):
            report.error(
                "invalid-evidence-id",
                f"{label} must use EVD-NNN format",
            )
        test_case_id = entry.get("test_case_id")
        if test_case_id not in case_ids:
            report.error(
                "unknown-case",
                f"{label} references unknown test case {test_case_id!r}",
            )
        finding_id = entry.get("finding_id")
        if finding_id is not None and finding_id not in finding_ids:
            report.error(
                "unknown-finding",
                f"{label} references unknown finding {finding_id!r}",
            )
        for required_field in (
            "description",
            "captured_at",
            "expected",
            "actual",
        ):
            if not isinstance(entry.get(required_field), str):
                report.error(
                    "missing-metadata",
                    f"{label} requires string field {required_field}",
                )

        processed_path = _validate_evidence_file(
            run_dir,
            entry.get("path"),
            entry.get("sha256"),
            f"{label} processed image",
            report,
        )
        original_path = _validate_evidence_file(
            run_dir,
            entry.get("original_path"),
            entry.get("original_sha256"),
            f"{label} original image",
            report,
        )
        if processed_path:
            referenced_image_paths.add(processed_path.resolve())
            if processed_path.is_file() and processed_path.stat().st_size > max_bytes:
                report.error(
                    "attachment-too-large",
                    f"{label} is {processed_path.stat().st_size} bytes; "
                    f"limit is {max_bytes}",
                )
        if original_path:
            referenced_image_paths.add(original_path.resolve())

        attachment = entry.get("attachment")
        if not isinstance(attachment, dict):
            report.error(
                "missing-attachment-state",
                f"{label} attachment must be an object",
            )
            attachment = {}
        status = attachment.get("status")
        if status not in ATTACHMENT_STATUSES:
            report.error(
                "invalid-attachment-state",
                f"{label} has invalid attachment status {status!r}",
            )
        if status == "uploaded" and not attachment.get(
            "external_tracking_id"
        ):
            report.error(
                "missing-tracking-id",
                f"{label} is uploaded but has no external tracking ID",
            )
        if status in {"blocked", "rejected"} and not attachment.get(
            "failure_reason"
        ):
            report.error(
                "missing-upload-reason",
                f"{label} is {status} but has no failure reason",
            )

    for test_case in cases:
        case_id = test_case.get("id")
        status = test_case.get("status")
        if not isinstance(case_id, str) or not case_id:
            report.error("missing-case-id", "Every test case requires an ID")
            continue
        if status not in CASE_STATUSES:
            report.error(
                "invalid-case-status",
                f"Test case {case_id} has invalid status {status!r}",
            )
        case_evidence = test_case.get("evidence_ids", [])
        if not isinstance(case_evidence, list):
            report.error(
                "invalid-reference-list",
                f"Test case {case_id} evidence_ids must be an array",
            )
            case_evidence = []
        for evidence_id in case_evidence:
            if evidence_id not in evidence_ids:
                report.error(
                    "unknown-evidence",
                    f"Test case {case_id} references {evidence_id!r}",
                )
        for finding_id in test_case.get("finding_ids", []):
            if finding_id not in finding_ids:
                report.error(
                    "unknown-finding",
                    f"Test case {case_id} references {finding_id!r}",
                )
        for dependency in test_case.get("dependencies", []):
            if dependency not in case_ids:
                report.error(
                    "unknown-dependency",
                    f"Test case {case_id} depends on {dependency!r}",
                )
        if (
            status in {"issue", "works_with_issue"}
            and not case_evidence
            and not test_case.get("evidence_exception")
        ):
            report.error(
                "issue-without-evidence",
                f"Test case {case_id} is {status} but has no evidence or "
                "evidence_exception",
            )

    for finding in findings:
        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not finding_id:
            report.error("missing-finding-id", "Every finding requires an ID")
            continue
        severity = finding.get("severity")
        if severity not in SEVERITIES:
            report.error(
                "invalid-severity",
                f"Finding {finding_id} has invalid severity {severity!r}",
            )
        for required_field in ("title", "area", "expected", "actual", "impact"):
            if not isinstance(finding.get(required_field), str) or not finding.get(
                required_field
            ):
                report.error(
                    "missing-finding-field",
                    f"Finding {finding_id} requires {required_field}",
                )
        steps = finding.get("steps")
        if not isinstance(steps, list) or not steps:
            report.error(
                "missing-reproduction",
                f"Finding {finding_id} requires reproduction steps",
            )
        finding_evidence = finding.get("evidence_ids", [])
        if not isinstance(finding_evidence, list):
            report.error(
                "invalid-reference-list",
                f"Finding {finding_id} evidence_ids must be an array",
            )
            finding_evidence = []
        for evidence_id in finding_evidence:
            if evidence_id not in evidence_ids:
                report.error(
                    "unknown-evidence",
                    f"Finding {finding_id} references {evidence_id!r}",
                )
        if not finding_evidence and not finding.get("evidence_exception"):
            report.error(
                "finding-without-evidence",
                f"Finding {finding_id} has no evidence or evidence_exception",
            )
        for case_id in finding.get("test_case_ids", []):
            if case_id not in case_ids:
                report.error(
                    "unknown-case",
                    f"Finding {finding_id} references {case_id!r}",
                )

    for submission in submissions:
        tracking_id = submission.get("tracking_id")
        if not isinstance(tracking_id, str) or not tracking_id:
            report.error(
                "missing-tracking-id",
                "Every submission requires a tracking_id",
            )
        for case_id in submission.get("test_case_ids", []):
            if case_id not in case_ids:
                report.error(
                    "unknown-case",
                    f"Submission {tracking_id!r} references {case_id!r}",
                )
        for finding_id in submission.get("finding_ids", []):
            if finding_id not in finding_ids:
                report.error(
                    "unknown-finding",
                    f"Submission {tracking_id!r} references {finding_id!r}",
                )

    evidence_root = run_dir / "evidence"
    if evidence_root.is_dir():
        actual_images = {
            path.resolve()
            for path in evidence_root.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        }
        for orphan in sorted(actual_images - referenced_image_paths):
            report.error(
                "orphaned-image",
                f"Image is not registered in the manifest: "
                f"{orphan.relative_to(run_dir.resolve()).as_posix()}",
            )
    if not evidence:
        report.warning("no-evidence", "The run contains no evidence entries")

    _validate_markdown_links(run_dir, report)
    return report
