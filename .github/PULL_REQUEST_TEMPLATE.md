## Summary

<!-- What changed and why? -->

## Checks

- [ ] `se --check` passes or the failure is explained.
- [ ] `se --check --json` remains read-only.
- [ ] Windows default behavior is unchanged: `se query` still uses Everything / `es.exe`.
- [ ] Non-interactive mode still rejects `-f/--fzf`.
- [ ] Timeout behavior still exits with `124` when the search budget is exhausted.

## Backend Changes

Complete this section if the PR changes backend selection or search execution.

- [ ] `--backend` behavior is explicit opt-in.
- [ ] Linux/POSIX backend warnings or fallbacks do not affect Windows default search.
- [ ] `-p/--path`, `--scope`, `-n/--max`, `--max-seconds`, `--stats`, `--log`, and `--caller codex --no-interactive` still work through the changed path.
- [ ] Missing backend command errors are clear and actionable.

## Notes

<!-- Any follow-up issues, skipped checks, or local environment constraints. -->

