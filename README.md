# Autonomous Testing Agent

Document-driven exploratory testing for web applications, with reproducible
findings, image evidence, Markdown reports, and intake-system submission
tracking.

The repository packages two complementary components:

- A publishable GitHub Copilot skill at
  `skills/bugbash-autopilot/SKILL.md`.
- A custom tester profile at
  `.github/agents/bug-bash-tester.agent.md`.

`.github/skills/bugbash-autopilot/SKILL.md` is a project-local bridge to the
canonical publishable skill, so contributors also get automatic discovery while
working in this repository.

The workflow was designed from a real end-to-end bug bash in which a tutorial
was converted into a test plan, executed through browser computer use, retried
to distinguish transient failures from defects, documented with screenshots,
and mapped into an external bug-intake checklist.

## Capabilities

- Extract test cases from tutorials and checklists.
- Execute UI, SQL, media, and long-running asynchronous checks.
- Persist test state so interrupted runs can resume.
- Capture screenshots immediately when relevant state is visible.
- Preserve original images while creating annotated or redacted copies.
- Compress evidence to an intake system's attachment limit.
- Correlate checks, findings, screenshots, task IDs, and external tracking IDs.
- Validate broken image links, missing evidence, duplicate IDs, and orphaned
  files.
- Generate detailed Markdown reports and evidence indexes.
- Record upload failures without falsely claiming that evidence was attached.
- Locate evidence later from either a local finding ID or external tracking ID.

## Install the skill

With GitHub CLI 2.90 or later:

```shell
gh skill install tmdaidevs/autonomous-testing-agent bugbash-autopilot
```

To use the custom agent in a repository, copy
`.github/agents/bug-bash-tester.agent.md` into that repository's
`.github/agents` directory.

## Development setup

```shell
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The installed command and the standalone skill script expose the same
interface:

```shell
bugbash-autopilot --help
python skills/bugbash-autopilot/scripts/bugbash-autopilot.py --help
```

## Quick start

Create an evidence run:

```shell
bugbash-autopilot init \
  --run-dir runs/my-app \
  --run-id my-app-2026-10-13 \
  --title "My application bug bash" \
  --source-document docs/tutorial.pdf \
  --target-url https://example.test
```

After a browser tool captures a screenshot, register it:

```shell
bugbash-autopilot add-evidence \
  --run-dir runs/my-app \
  --source screenshots/table-card.png \
  --case-id B1-UX-2 \
  --finding-id BUG-003 \
  --description "Table card displays undefined as its resource type" \
  --expected "The card displays Multimodal" \
  --actual "The card displays undefined" \
  --highlight 420,260,300,90
```

Validate the complete run and generate its report:

```shell
bugbash-autopilot validate --run-dir runs/my-app
bugbash-autopilot report --run-dir runs/my-app
```

## Evidence model

Each run contains portable JSON plus evidence files:

```text
runs/my-app/
├── results.json
├── Bug-Bash-Report.md
└── evidence/
    ├── manifest.json
    ├── originals/
    │   └── B1-UX-2/
    │       └── 001-B1-UX-2-table-card.png
    └── processed/
        └── B1-UX-2/
            └── 001-B1-UX-2-table-card.png
```

The manifest records the check, finding, timestamp, URL, action, expected
result, actual result, hashes, image dimensions, upload state, and external
tracking ID. An original is never overwritten by annotation, redaction, or
compression.

## Workflow

```mermaid
flowchart LR
    A[Guide or checklist] --> B[Test plan]
    B --> C[Preflight and safety review]
    C --> D[Browser, SQL, or API execution]
    D --> E[Retry and classify]
    E --> F[Capture and redact evidence]
    F --> G[Markdown report]
    G --> H[Intake submission]
    H --> I[Verify persistence]
    I --> J[Triage follow-up]
```

The skill requires destructive tests to use an explicitly disposable target or
receive user approval. It also requires transient concurrency, throttling, and
provider failures to be rerun under controlled conditions before being labeled
as product defects.

## Public-repository privacy policy

This public repository contains only synthetic test data and generated image
fixtures. Real product screenshots, internal URLs, credentials, access tokens,
customer data, and personal information must remain outside source control
unless they have been explicitly reviewed and redacted.

Private run artifacts are ignored by default through `.gitignore`.

## Synthetic example

`examples/synthetic-run` demonstrates the complete artifact set without using
real product data. Regenerate and validate it with:

```shell
python scripts/create_synthetic_example.py --force
bugbash-autopilot validate --run-dir examples/synthetic-run
```

## Testing

```shell
pytest
```

## License

[MIT](LICENSE)
