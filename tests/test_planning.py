from __future__ import annotations

from pathlib import Path

from bugbash_autopilot.planning import extract_plan


def test_extract_plan_from_headings_and_checkboxes(tmp_path: Path) -> None:
    source = tmp_path / "guide.md"
    source.write_text(
        "## B1-UX-1 - Create a table\n\n"
        "- [ ] B1-SQL-2: Verify the row count\n"
        "- [x] Check keyboard navigation\n",
        encoding="utf-8",
    )

    plan = extract_plan(source)

    assert [case["id"] for case in plan["test_cases"]] == [
        "B1-UX-1",
        "B1-SQL-2",
        "CHECK-001",
    ]
    assert plan["test_cases"][2]["title"] == "Check keyboard navigation"
    assert plan["requires_review"] is True
