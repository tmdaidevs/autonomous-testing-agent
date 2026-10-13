---
name: bugbash-autopilot
description: Execute document-driven web application bug bashes autonomously, including browser and SQL checks, controlled retries, screenshot evidence, Markdown reports, intake submission, persistence verification, and triage follow-up. Use when a user provides a tutorial, checklist, test plan, or application and asks to test it or report issues.
license: MIT
---

# Bug Bash Autopilot

Turn a guide, tutorial, or checklist into a resumable evidence-first test run.
Complete the requested workflow rather than stopping after planning.

Read the supporting references when their phase becomes relevant:

- [Workflow](references/workflow.md)
- [Evidence policy](references/evidence-policy.md)
- [Classification and retries](references/classification.md)
- [Safety and privacy](references/safety.md)
- [Intake adapters](references/intake-adapters.md)
- [Run state](references/run-state.md)
- [Jev Ultrafast adapter](references/jev-ultrafast.md)

## Non-negotiable rules

1. Follow the supplied document in order unless a dependency requires a safe
   reordering.
2. Keep a persistent ledger of every check, attempt, finding, evidence item,
   dependency, asynchronous task, and submission.
3. Capture evidence while the relevant result is still visible.
4. Every confirmed UI issue needs at least one screenshot. If capture is
   impossible, record a specific `evidence_exception`; never silently omit it.
5. Preserve the original image and create a separate processed copy.
6. Redact credentials, tokens, personal information, private content, and
   unrelated browser chrome before sharing evidence.
7. Rerun likely concurrency, throttling, provider, or timing failures under
   controlled serial conditions before classifying them as product defects.
8. Do not perform destructive testing unless the document identifies a
   disposable target or the user explicitly approves the exact action.
9. Never interpret an outer `Completed` status as proof of success. Inspect the
   result payload, row-level values, derived content, and user-visible output.
10. Verify that submitted records and attachments persist. A click on Submit is
    not sufficient.
11. If an attachment fails, retain the local evidence, record the exact reason,
    and submit text only when the user's policy permits it.
12. Do not claim that evidence was uploaded unless the intake system confirms
    it.

## Required capabilities

Use the tools available in the host:

- Browser computer use for authentication, navigation, forms, media playback,
  screenshots, console inspection, and upload verification.
- File and document tools for PDF, Word, spreadsheet, presentation, Markdown,
  and plain-text guides.
- SQL or application query tools when the test plan requires data validation.
- Terminal execution for the evidence helper and product-specific CLI tools.
- A persistent state store, preferably SQLite, when the host provides one.
- Issue, REST, or intake-system tools when they are available and appropriate.

Do not block merely because a preferred native integration is absent. Use the
available browser or command-line route and record the chosen adapter.

## Operating procedure

### 1. Intake and preflight

1. Identify the source document, target application, intended account,
   environment, data scope, and intake destination.
2. Confirm whether an existing database, workspace, or project should be
   reused.
3. Determine whether the run contains destructive actions.
4. Identify privacy constraints and the maximum attachment size.
5. Create the run directory and state files:

   ```shell
   bugbash-autopilot init \
     --run-dir runs/<run-id> \
     --run-id <run-id> \
     --title "<title>" \
     --source-document "<guide-path>" \
     --target-url "<application-url>"
   ```

Use the standalone script if the package is not installed:

```shell
python scripts/bugbash-autopilot.py <command> ...
```

### 2. Extract a test plan

Convert PDF, Word, spreadsheet, or presentation content to text with the
appropriate document tool. Preserve:

- Original section and check identifiers.
- Expected values and counts.
- Exact queries and commands.
- Required accounts, databases, tables, and files.
- Dependencies between checks.
- Destructive or irreversible steps.
- Ambiguities and contradictions in the guide.

For Markdown checklists, the helper can create a plan skeleton:

```shell
bugbash-autopilot plan --input guide.md --output plan.json
```

Merge the reviewed cases into `results.json`. Do not trust heuristic extraction
without checking it against the source.

### 3. Execute and persist

For each ready test case:

1. Record the attempt and starting context.
2. Verify the active account, workspace, database, and object before acting.
3. Execute the smallest independent action.
4. Poll asynchronous work with product task APIs when available.
5. Inspect final state and result content.
6. Capture relevant evidence.
7. Classify the result.
8. Persist the result before moving to the next case.

Serialize operations that touch the same mutable parent resource. Independent
resources may be tested in parallel only when that does not make evidence or
failure attribution ambiguous.

#### Optional fast browser execution

Use the Jev Ultrafast adapter for narrow, non-destructive goals involving
ordinary visible DOM or ARIA controls:

```shell
bugbash-autopilot jev-run \
  --run-dir runs/<run-id> \
  --case-id <check-id> \
  --url <start-url> \
  --goal "<narrow goal>" \
  --expected-url-regex "<required URL pattern>" \
  --expected-text "<required visible text>"
```

Jev selecting `DONE` is not proof of success. Supply deterministic completion
predicates or verify the final state independently with computer use. Read
[jev-ultrafast.md](references/jev-ultrafast.md) before enabling it. Route file
uploads, frames, shadow DOM, canvas, popup tabs, nested scrolling, media,
visual checks, console/network inspection, and blocked goals to computer use.

### 4. Retry and classify

Use [classification.md](references/classification.md). In particular:

- Retry concurrency conflicts after conflicting work completes.
- Retry throttled or provider-backed operations serially with bounded backoff.
- Recheck delayed derived content after the documented processing interval.
- Keep each attempt; do not overwrite the first failure with the retry.

Classify a failure as a product defect only when the controlled rerun still
violates the requirement, or when the transient behavior itself violates a
documented reliability or UX requirement.

### 5. Capture image evidence

Capture the smallest screenshot that proves the observation, while retaining
enough context to identify the product surface. Register it immediately:

```shell
bugbash-autopilot add-evidence \
  --run-dir runs/<run-id> \
  --source <captured-image> \
  --case-id <check-id> \
  --finding-id <finding-id> \
  --description "<what the image proves>" \
  --page-url "<current-url>" \
  --action "<action just performed>" \
  --expected "<expected state>" \
  --actual "<visible state>"
```

Use `--redact x,y,width,height` for sensitive regions and
`--highlight x,y,width,height` for the defect. Both options may be repeated.
Review the processed image before submission.

For audio and video checks, include the visible player state and playback
position, then record the audible or visual verification in text. A static
screenshot alone cannot prove sound quality or continuous playback.

### 6. Report

Write direct, reproducible findings containing:

- Stable finding ID and severity.
- Product area and affected check IDs.
- Preconditions and exact reproduction steps.
- Expected and actual behavior.
- Impact.
- Controlled retry outcome.
- Screenshot and diagnostic references.
- Workaround or recommendation when known.
- External tracking IDs after submission.

Generate the report and validate all references:

```shell
bugbash-autopilot report --run-dir runs/<run-id>
bugbash-autopilot validate --run-dir runs/<run-id>
```

### 7. Submit and verify

Map each result to the intake system's predefined checks before creating
standalone bugs. Avoid duplicate reports.

For every submission:

1. Fill the form with exact observed behavior and reproduction steps.
2. Attach the most relevant processed screenshot when supported.
3. Submit.
4. Reopen the reported-record view.
5. Confirm the record, status, tracking ID, and attachment indicator.
6. Record the external tracking ID and upload state in the manifest.

Update attachment state:

```shell
bugbash-autopilot record-upload \
  --run-dir runs/<run-id> \
  --evidence-id EVD-001 \
  --status uploaded \
  --tracking-id BB-12345678
```

When upload is blocked:

```shell
bugbash-autopilot record-upload \
  --run-dir runs/<run-id> \
  --evidence-id EVD-001 \
  --status blocked \
  --reason "Sign in again before submitting a screenshot."
```

### 8. Close and support triage

Before declaring completion:

- Every source check has a terminal status.
- Every issue is represented in the report and intake mapping.
- Every issue has evidence or an evidence exception.
- All local image links resolve.
- No unregistered images remain.
- Submission totals and unique tracking IDs reconcile.
- Sensitive data has been reviewed.

Find later evidence by local finding ID, check ID, evidence ID, or external
tracking ID:

```shell
bugbash-autopilot lookup --run-dir runs/<run-id> --id BB-12345678
```

Provide triage with the processed image and a one-sentence explanation of what
it shows. Retain the original locally for auditability.

## Completion standard

A run is complete only when execution state, evidence, reports, and external
submission state are mutually consistent and the validator exits successfully.
