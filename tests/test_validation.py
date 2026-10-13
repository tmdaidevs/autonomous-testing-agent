from __future__ import annotations

from pathlib import Path

from PIL import Image

from bugbash_autopilot.evidence import initialize_run
from bugbash_autopilot.io_utils import read_json, write_json
from bugbash_autopilot.validation import validate_run


def _write_issue_without_evidence(run_dir: Path) -> None:
    initialize_run(run_dir, "validation-run", "Validation run")
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"] = [
        {
            "id": "CASE-001",
            "title": "A failing case",
            "status": "issue",
            "expected": "Expected",
            "actual": "Actual",
            "dependencies": [],
            "finding_ids": ["BUG-001"],
            "evidence_ids": [],
            "attempts": [],
        }
    ]
    results["findings"] = [
        {
            "id": "BUG-001",
            "title": "A defect",
            "severity": "high",
            "area": "Example",
            "test_case_ids": ["CASE-001"],
            "steps": ["Perform an action."],
            "expected": "Expected",
            "actual": "Actual",
            "impact": "The workflow is blocked.",
            "evidence_ids": [],
        }
    ]
    write_json(results_path, results)


def test_validation_requires_evidence_for_issues(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_issue_without_evidence(run_dir)

    report = validate_run(run_dir)
    codes = {message.code for message in report.errors}
    assert "issue-without-evidence" in codes
    assert "finding-without-evidence" in codes


def test_validation_accepts_explicit_evidence_exception(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _write_issue_without_evidence(run_dir)
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"][0]["evidence_exception"] = (
        "Browser terminated before capture."
    )
    results["findings"][0]["evidence_exception"] = (
        "Browser terminated before capture."
    )
    write_json(results_path, results)

    report = validate_run(run_dir)
    assert report.valid


def test_validation_detects_orphaned_image_and_broken_link(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    initialize_run(run_dir, "orphan-run", "Orphan run")
    orphan = run_dir / "evidence" / "orphan.png"
    Image.new("RGB", (20, 20), "white").save(orphan)
    (run_dir / "Report.md").write_text(
        "![missing](evidence/missing.png)\n",
        encoding="utf-8",
    )

    report = validate_run(run_dir)
    codes = {message.code for message in report.errors}
    assert "orphaned-image" in codes
    assert "broken-markdown-link" in codes
