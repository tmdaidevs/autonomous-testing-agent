from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from bugbash_autopilot.evidence import (
    add_evidence,
    initialize_run,
    lookup_evidence,
    parse_rectangle,
    record_upload,
)
from bugbash_autopilot.io_utils import read_json, write_json
from bugbash_autopilot.validation import validate_run


def _source_image(path: Path) -> None:
    image = Image.new("RGB", (800, 600), "white")
    image.save(path)


def _issue_run(run_dir: Path) -> Path:
    initialize_run(run_dir, "run-1", "Example run")
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"] = [
        {
            "id": "CASE-001",
            "title": "Display type",
            "status": "issue",
            "expected": "A type is shown.",
            "actual": "undefined is shown.",
            "dependencies": [],
            "finding_ids": ["BUG-001"],
            "evidence_ids": [],
            "attempts": [],
        }
    ]
    results["findings"] = [
        {
            "id": "BUG-001",
            "title": "Type is undefined",
            "severity": "medium",
            "area": "Browsing",
            "test_case_ids": ["CASE-001"],
            "steps": ["Open the page.", "Inspect the card."],
            "expected": "A type is shown.",
            "actual": "undefined is shown.",
            "impact": "The card is ambiguous.",
            "recommendation": "Render a fallback.",
            "evidence_ids": [],
            "external_tracking_ids": [],
        }
    ]
    write_json(results_path, results)
    return results_path


def test_add_evidence_preserves_original_and_links_results(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    results_path = _issue_run(run_dir)
    source = tmp_path / "source.png"
    _source_image(source)

    entry = add_evidence(
        run_dir=run_dir,
        source=source,
        test_case_id="CASE-001",
        finding_id="BUG-001",
        description="Card displays undefined",
        expected="A type is shown.",
        actual="undefined is shown.",
        redactions=[(10, 10, 40, 20)],
        highlights=[(100, 100, 200, 80)],
    )

    original = run_dir / entry["original_path"]
    processed = run_dir / entry["path"]
    assert original.is_file()
    assert processed.is_file()
    assert original.read_bytes() != processed.read_bytes()
    assert entry["original_sha256"] != entry["sha256"]

    results = read_json(results_path)
    assert results["test_cases"][0]["evidence_ids"] == ["EVD-001"]
    assert results["findings"][0]["evidence_ids"] == ["EVD-001"]
    assert validate_run(run_dir).valid


def test_record_upload_requires_tracking_id_and_supports_lookup(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    _issue_run(run_dir)
    source = tmp_path / "source.png"
    _source_image(source)
    entry = add_evidence(
        run_dir=run_dir,
        source=source,
        test_case_id="CASE-001",
        finding_id="BUG-001",
        description="Card displays undefined",
    )

    with pytest.raises(ValueError, match="tracking ID"):
        record_upload(run_dir, entry["evidence_id"], "uploaded")

    record_upload(
        run_dir,
        entry["evidence_id"],
        "uploaded",
        tracking_id="EXT-123",
    )
    matches = lookup_evidence(run_dir, "EXT-123")
    assert [item["evidence_id"] for item in matches] == ["EVD-001"]
    results = read_json(run_dir / "results.json")
    assert results["findings"][0]["external_tracking_ids"] == ["EXT-123"]


def test_parse_rectangle_rejects_invalid_values() -> None:
    assert parse_rectangle("1,2,3,4") == (1, 2, 3, 4)
    with pytest.raises(ValueError):
        parse_rectangle("1,2,3")
    with pytest.raises(ValueError):
        parse_rectangle("1,2,-3,4")
