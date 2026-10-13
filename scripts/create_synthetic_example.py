from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SKILL_SCRIPTS = (
    REPOSITORY_ROOT
    / "skills"
    / "bugbash-autopilot"
    / "scripts"
)
sys.path.insert(0, str(SKILL_SCRIPTS))

from bugbash_autopilot.evidence import (  # noqa: E402
    add_evidence,
    initialize_run,
    record_upload,
)
from bugbash_autopilot.io_utils import read_json, write_json  # noqa: E402
from bugbash_autopilot.reporting import generate_report  # noqa: E402
from bugbash_autopilot.validation import validate_run  # noqa: E402


def _draw_synthetic_screenshot(destination: Path) -> None:
    image = Image.new("RGB", (1280, 720), "#f6f7fb")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.rectangle((0, 0, 1280, 64), fill="#20243a")
    draw.text((32, 22), "Example Data Workspace", fill="white", font=font)
    draw.rectangle((0, 64, 210, 720), fill="#e9ebf3")
    draw.text((24, 104), "Databases", fill="#30364d", font=font)
    draw.text((24, 138), "Tables", fill="#30364d", font=font)

    draw.text((260, 100), "Tables", fill="#20243a", font=font)
    draw.rounded_rectangle(
        (260, 150, 750, 390),
        radius=12,
        fill="white",
        outline="#c8ccda",
        width=2,
    )
    draw.text(
        (300, 198),
        "example_documents",
        fill="#20243a",
        font=font,
    )
    draw.text((300, 244), "undefined", fill="#8a3143", font=font)
    draw.text((300, 302), "21 items", fill="#555d75", font=font)
    draw.rectangle((600, 320, 700, 356), fill="#5b5bd6")
    draw.text((628, 333), "Open", fill="white", font=font)

    draw.text(
        (260, 440),
        "Synthetic fixture - no real product or customer data",
        fill="#555d75",
        font=font,
    )
    image.save(destination, format="PNG", optimize=True)


def create_example(run_dir: Path, force: bool) -> None:
    if run_dir.exists():
        if not force:
            raise FileExistsError(
                f"{run_dir} already exists. Pass --force to regenerate it."
            )
        shutil.rmtree(run_dir)

    initialize_run(
        run_dir=run_dir,
        run_id="synthetic-webapp-2026-10-13",
        title="Synthetic Web Application Bug Bash",
        source_document="synthetic-tutorial.md",
        target_url="https://example.test/databases/demo",
        max_attachment_bytes=2 * 1024 * 1024,
    )
    results_path = run_dir / "results.json"
    results = read_json(results_path)
    results["test_cases"] = [
        {
            "id": "SETUP-001",
            "title": "Open the database workspace",
            "status": "works",
            "expected": "The workspace opens and lists available tables.",
            "actual": "The workspace opened and displayed the Tables page.",
            "dependencies": [],
            "finding_ids": [],
            "evidence_ids": [],
            "attempts": [
                {
                    "started_at": "2026-10-13T07:45:00Z",
                    "completed_at": "2026-10-13T07:45:05Z",
                    "outcome": "works",
                    "notes": "Synthetic successful precondition.",
                }
            ],
        },
        {
            "id": "BROWSE-001",
            "title": "Understand the resource type from the table card",
            "status": "issue",
            "expected": "The table card displays a meaningful resource type.",
            "actual": "The table card displays the literal value undefined.",
            "dependencies": ["SETUP-001"],
            "finding_ids": ["BUG-001"],
            "evidence_ids": [],
            "attempts": [
                {
                    "started_at": "2026-10-13T07:46:00Z",
                    "completed_at": "2026-10-13T07:46:10Z",
                    "outcome": "issue",
                    "notes": "The same value remained after a serial reload.",
                }
            ],
        },
    ]
    results["findings"] = [
        {
            "id": "BUG-001",
            "title": "Table card displays undefined as its resource type",
            "severity": "medium",
            "area": "Database browsing",
            "test_case_ids": ["BROWSE-001"],
            "steps": [
                "Open the example database workspace.",
                "Navigate to Tables.",
                "Inspect the example_documents card.",
            ],
            "expected": "The card displays a resource type such as Multimodal.",
            "actual": "The card displays the literal value undefined.",
            "impact": "Users cannot identify the table type and the resource list appears broken.",
            "recommendation": "Render the resolved table type and use an explicit fallback label when metadata is unavailable.",
            "evidence_ids": [],
            "external_tracking_ids": [],
        }
    ]
    write_json(results_path, results)

    with tempfile.TemporaryDirectory() as temporary:
        source = Path(temporary) / "synthetic-table-card.png"
        _draw_synthetic_screenshot(source)
        entry = add_evidence(
            run_dir=run_dir,
            source=source,
            test_case_id="BROWSE-001",
            finding_id="BUG-001",
            description=(
                "example_documents card displays undefined below the table name"
            ),
            page_url="https://example.test/databases/demo/tables",
            action="Opened the Tables page and inspected the resource card",
            expected="The card displays a meaningful resource type.",
            actual="The card displays undefined.",
            captured_at="2026-10-13T07:46:08Z",
            highlights=[(280, 225, 220, 50)],
        )

    record_upload(
        run_dir=run_dir,
        evidence_id=entry["evidence_id"],
        status="uploaded",
        tracking_id="DEMO-1234",
    )
    results = read_json(results_path)
    results["submissions"] = [
        {
            "tracking_id": "DEMO-1234",
            "test_case_ids": ["BROWSE-001"],
            "finding_ids": ["BUG-001"],
            "status": "Awaiting triage",
            "submitted_at": "2026-10-13T07:50:00Z",
        }
    ]
    write_json(results_path, results)

    generate_report(run_dir, run_dir / "Bug-Bash-Report.md")
    (run_dir / "README.md").write_text(
        "# Synthetic run\n\n"
        "This fixture demonstrates a complete evidence-first bug-bash run. "
        "All names, URLs, tracking IDs, and screenshots are synthetic.\n",
        encoding="utf-8",
        newline="\n",
    )

    validation = validate_run(run_dir)
    if validation.errors:
        messages = "\n".join(
            f"[{item.code}] {item.message}" for item in validation.errors
        )
        raise RuntimeError(f"Synthetic run failed validation:\n{messages}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=REPOSITORY_ROOT / "examples" / "synthetic-run",
    )
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    create_example(arguments.run_dir.resolve(), arguments.force)
    print(f"Created {arguments.run_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
