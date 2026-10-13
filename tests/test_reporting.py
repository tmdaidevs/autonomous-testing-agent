from __future__ import annotations

from pathlib import Path

from PIL import Image

from bugbash_autopilot.evidence import (
    add_evidence,
    initialize_run,
    record_upload,
)
from bugbash_autopilot.io_utils import read_json, write_json
from bugbash_autopilot.reporting import generate_report
from bugbash_autopilot.validation import validate_run


def test_report_embeds_evidence_and_tracking_id(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    initialize_run(run_dir, "report-run", "Report run")
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"] = [
        {
            "id": "CASE-001",
            "title": "Inspect the card",
            "status": "issue",
            "expected": "Type",
            "actual": "undefined",
            "dependencies": [],
            "finding_ids": ["BUG-001"],
            "evidence_ids": [],
            "attempts": [],
        }
    ]
    results["findings"] = [
        {
            "id": "BUG-001",
            "title": "Undefined type",
            "severity": "medium",
            "area": "Browsing",
            "test_case_ids": ["CASE-001"],
            "steps": ["Open the card."],
            "expected": "Type",
            "actual": "undefined",
            "impact": "Ambiguous resource.",
            "recommendation": "Render the type.",
            "evidence_ids": [],
            "external_tracking_ids": [],
        }
    ]
    write_json(results_path, results)

    source = tmp_path / "source.png"
    Image.new("RGB", (320, 240), "white").save(source)
    entry = add_evidence(
        run_dir,
        source,
        "CASE-001",
        "Card displays undefined",
        finding_id="BUG-001",
    )
    record_upload(
        run_dir,
        entry["evidence_id"],
        "uploaded",
        tracking_id="EXT-123",
    )
    results = read_json(results_path)
    results["submissions"] = [
        {
            "tracking_id": "EXT-123",
            "test_case_ids": ["CASE-001"],
            "finding_ids": ["BUG-001"],
            "status": "Open",
        }
    ]
    write_json(results_path, results)

    output = run_dir / "Bug-Bash-Report.md"
    content = generate_report(run_dir, output)

    assert "BUG-001 - Undefined type" in content
    assert "EXT-123" in content
    assert "![Card displays undefined]" in content
    assert validate_run(run_dir).valid
