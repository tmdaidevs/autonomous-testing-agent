# Contributing

Contributions are welcome when they preserve the project's evidence-first and
safety-first behavior.

## Development

```shell
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

Before opening a pull request:

1. Add or update tests for behavioral changes.
2. Run `pytest`.
3. Regenerate the synthetic example when its schema or output changes.
4. Run `bugbash-autopilot validate --run-dir examples/synthetic-run`.
5. Run `gh skill publish --dry-run` when changing the skill metadata.

## Privacy

Do not contribute real credentials, tokens, internal URLs, customer data,
private emails, or unreviewed product screenshots. Use synthetic fixtures or
clearly redacted examples.

## Design expectations

- Preserve original evidence files.
- Report validation failures explicitly.
- Never turn a failed upload into a success-shaped result.
- Require an explanation when an issue has no image evidence.
- Keep destructive test actions gated behind explicit approval or a named
  disposable target.
