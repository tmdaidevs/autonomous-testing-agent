# Workflow

## Lifecycle

### Intake

Record the source document, target URL, environment, account, data scope,
intake destination, and evidence policy. Reuse named user resources.

### Plan

Create one record for each requirement, query, interaction, expected count, and
documented negative test. Keep source identifiers. Record dependencies instead
of relying on list order.

### Preflight

Confirm authentication, selected account, database or workspace, target object,
browser permissions, attachment limits, and disposable resources.

### Execute

Run the smallest action that proves the requirement. Save the attempt before
moving on. Use task APIs or result queries instead of relying only on chat
messages or progress spinners.

### Retry

Use bounded, reason-specific retries. A retry is an additional attempt, not a
replacement for prior evidence.

### Evidence

Capture the visible result immediately. Save diagnostics that explain the same
event, such as request IDs, task IDs, console errors, or SQL results.

### Classify

Separate product defects, documentation gaps, environment failures, transient
constraints, and improvements. Record the evidence supporting the distinction.

### Report

Write concise findings with exact reproduction steps, expected behavior, actual
behavior, impact, evidence, and recommendation.

### Submit

Prefer an existing checklist case when it accurately represents the finding.
Create standalone bugs only for uncovered behavior.

### Verify

Reopen submission history and verify the persisted record, tracking ID, status,
and attachment. Reconcile all local and external counts.

### Triage

Support later questions by looking up evidence through the manifest. Share the
processed image, not an unreviewed original.

## Resume protocol

At the beginning of a resumed run:

1. Load `results.json` and `evidence/manifest.json`.
2. Reconcile in-progress cases with the current product state.
3. Do not rerun completed destructive actions.
4. Resume cases whose dependencies are complete.
5. Preserve prior attempts and add a new attempt for resumed work.

## Parallelism

Parallelize only independent read-only or separate-resource checks. Serialize:

- DDL or configuration changes on one parent resource and its children.
- Multiple submissions through one browser form.
- AI-backed tasks when the provider throttles concurrent requests.
- Any interaction whose result would be ambiguous when multiple tabs change.
