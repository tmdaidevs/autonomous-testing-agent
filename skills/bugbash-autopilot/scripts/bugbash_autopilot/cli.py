from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .evidence import (
    ATTACHMENT_STATUSES,
    EvidenceError,
    add_evidence,
    initialize_run,
    lookup_evidence,
    parse_rectangle,
    record_upload,
)
from .planning import write_plan
from .reporting import generate_report
from .validation import validate_run


def _run_dir(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bugbash-autopilot",
        description=(
            "Manage screenshot evidence and reports for autonomous bug-bash runs."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Create a new run directory and evidence manifest.",
    )
    init_parser.add_argument("--run-dir", required=True, type=_run_dir)
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--title", required=True)
    init_parser.add_argument("--source-document")
    init_parser.add_argument("--target-url")
    init_parser.add_argument(
        "--max-attachment-mb",
        type=float,
        default=2.0,
        help="Maximum processed image size in MiB (default: 2).",
    )

    plan_parser = subparsers.add_parser(
        "plan",
        help="Extract a reviewable test-plan skeleton from Markdown.",
    )
    plan_parser.add_argument("--input", required=True, type=Path)
    plan_parser.add_argument("--output", required=True, type=Path)

    add_parser = subparsers.add_parser(
        "add-evidence",
        help="Preserve, process, and register a screenshot.",
    )
    add_parser.add_argument("--run-dir", required=True, type=_run_dir)
    add_parser.add_argument("--source", required=True, type=Path)
    add_parser.add_argument("--case-id", required=True)
    add_parser.add_argument("--finding-id")
    add_parser.add_argument("--description", required=True)
    add_parser.add_argument("--page-url")
    add_parser.add_argument("--action")
    add_parser.add_argument("--expected", default="")
    add_parser.add_argument("--actual", default="")
    add_parser.add_argument("--captured-at")
    add_parser.add_argument(
        "--redact",
        action="append",
        default=[],
        metavar="X,Y,WIDTH,HEIGHT",
    )
    add_parser.add_argument(
        "--highlight",
        action="append",
        default=[],
        metavar="X,Y,WIDTH,HEIGHT",
    )
    add_parser.add_argument("--max-bytes", type=int)

    upload_parser = subparsers.add_parser(
        "record-upload",
        help="Record verified intake-system attachment state.",
    )
    upload_parser.add_argument("--run-dir", required=True, type=_run_dir)
    upload_parser.add_argument("--evidence-id", required=True)
    upload_parser.add_argument(
        "--status",
        required=True,
        choices=sorted(ATTACHMENT_STATUSES),
    )
    upload_parser.add_argument("--tracking-id")
    upload_parser.add_argument("--reason")

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate run state, images, links, hashes, and references.",
    )
    validate_parser.add_argument("--run-dir", required=True, type=_run_dir)
    validate_parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return a failure exit code when warnings exist.",
    )

    report_parser = subparsers.add_parser(
        "report",
        help="Generate a Markdown report from run state.",
    )
    report_parser.add_argument("--run-dir", required=True, type=_run_dir)
    report_parser.add_argument(
        "--output",
        type=Path,
        default=Path("Bug-Bash-Report.md"),
    )

    lookup_parser = subparsers.add_parser(
        "lookup",
        help="Find evidence by evidence, check, finding, or tracking ID.",
    )
    lookup_parser.add_argument("--run-dir", required=True, type=_run_dir)
    lookup_parser.add_argument("--id", required=True)

    return parser


def _execute(arguments: argparse.Namespace) -> int:
    if arguments.command == "init":
        if arguments.max_attachment_mb <= 0:
            raise ValueError("--max-attachment-mb must be greater than zero")
        max_bytes = int(arguments.max_attachment_mb * 1024 * 1024)
        results_path, manifest_path = initialize_run(
            run_dir=arguments.run_dir,
            run_id=arguments.run_id,
            title=arguments.title,
            source_document=arguments.source_document,
            target_url=arguments.target_url,
            max_attachment_bytes=max_bytes,
        )
        print(f"Created {results_path}")
        print(f"Created {manifest_path}")
        return 0

    if arguments.command == "plan":
        plan = write_plan(arguments.input, arguments.output)
        print(
            f"Wrote {len(plan['test_cases'])} candidate checks to "
            f"{arguments.output}"
        )
        return 0

    if arguments.command == "add-evidence":
        entry = add_evidence(
            run_dir=arguments.run_dir,
            source=arguments.source.expanduser().resolve(),
            test_case_id=arguments.case_id,
            finding_id=arguments.finding_id,
            description=arguments.description,
            page_url=arguments.page_url,
            action=arguments.action,
            expected=arguments.expected,
            actual=arguments.actual,
            captured_at=arguments.captured_at,
            redactions=[
                parse_rectangle(value) for value in arguments.redact
            ],
            highlights=[
                parse_rectangle(value) for value in arguments.highlight
            ],
            max_bytes=arguments.max_bytes,
        )
        print(json.dumps(entry, indent=2))
        return 0

    if arguments.command == "record-upload":
        entry = record_upload(
            run_dir=arguments.run_dir,
            evidence_id=arguments.evidence_id,
            status=arguments.status,
            tracking_id=arguments.tracking_id,
            reason=arguments.reason,
        )
        print(json.dumps(entry["attachment"], indent=2))
        return 0

    if arguments.command == "validate":
        report = validate_run(arguments.run_dir)
        for message in report.errors:
            print(f"ERROR [{message.code}] {message.message}")
        for message in report.warnings:
            print(f"WARNING [{message.code}] {message.message}")
        print(
            f"Validation: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s)"
        )
        if report.errors or (arguments.strict_warnings and report.warnings):
            return 1
        return 0

    if arguments.command == "report":
        output = arguments.output
        if not output.is_absolute():
            output = arguments.run_dir / output
        generate_report(arguments.run_dir, output.resolve())
        print(f"Wrote {output.resolve()}")
        return 0

    if arguments.command == "lookup":
        matches = lookup_evidence(arguments.run_dir, arguments.id)
        print(json.dumps(matches, indent=2))
        return 0 if matches else 1

    raise ValueError(f"Unsupported command: {arguments.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        return _execute(arguments)
    except (EvidenceError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
