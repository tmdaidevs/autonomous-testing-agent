# Repository instructions

- Keep the skill portable: files required at runtime must live under
  `skills/bugbash-autopilot`.
- Keep `.github/skills/bugbash-autopilot/SKILL.md` as a small project-local
  bridge; do not duplicate the canonical implementation there.
- Use synthetic data in tests and examples.
- Never commit real bug-bash screenshots or private product URLs.
- Preserve original images; write annotations and redactions to processed
  copies.
- Treat missing files, invalid manifests, failed uploads, and unverifiable
  persistence as explicit failures.
- Add tests for validation, report generation, and evidence transformations.
- Keep the command-line interface backward compatible within a minor release.
