# Intake Adapters

## Adapter contract

Every intake path must support these logical operations, even when implemented
through browser computer use:

1. Discover predefined checks.
2. Search for an existing report.
3. Create or update a report.
4. Attach processed evidence when supported.
5. Verify the persisted record.
6. Return a stable tracking ID.
7. Record the initial triage state.

## Browser checklist application

- Read every predefined case before submitting standalone bugs.
- Map local findings to the closest accurate case.
- Keep one browser submission active at a time.
- After submission, open the reported-history view.
- Verify title, result, tracking ID, and attachment state.
- Reconcile the visible record count with the local submission log.

## GitHub Issues

- Check repository issue templates first.
- Search for duplicate open and closed issues.
- Include reproduction steps, expected and actual behavior, environment, impact,
  and evidence.
- Use private security reporting for vulnerabilities.
- Do not upload sensitive evidence to a public issue.

## REST or command-line APIs

- Use documented authentication sources without printing credentials.
- Treat non-2xx responses as failures.
- Parse and retain returned IDs.
- Fetch the created object to verify persistence.
- Use idempotency keys when the API supports them.

## Attachment limitations

When a form has no attachment field, set the evidence state to
`not_supported`. When upload is present but fails, use `blocked` or `rejected`
with the exact reason. Do not omit the distinction from the submission log.
