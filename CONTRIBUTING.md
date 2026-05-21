# Contributing

`se` is Windows-first local search tooling built around Everything / `es.exe`.
Linux and other backends are welcome, but they must not disturb the existing
Windows default path.

## Ground Rules

- Keep `se query` on Windows backed by Everything / `es.exe` unless an issue
  explicitly changes that behavior.
- Treat Linux/POSIX backends as explicit opt-in paths first, for example
  `--backend fd` or `--backend arch-linux`.
- Preserve agent-safe behavior: path and scope limits, result limits, timeout,
  stats, logging, and the non-interactive `fzf` guard.
- Keep `--check` read-only. It must not start services, install packages,
  rewrite config, or append logs.
- Keep `--doctor` as the repair path. Any mutation belongs there, not in
  `--check`.
- Prefer small, reviewable changes over broad rewrites of `cmd_search`.

## Before Opening A PR

Run the read-only health check:

```powershell
se --check
se --check --json
```

For changes that affect Codex or other non-interactive agents, verify the safe
mode path:

```powershell
se --caller codex --no-interactive --literal -n 10 "query"
```

If you change timeout behavior, confirm timeout remains an expected failure and
exits with `124`.

## Backend Changes

Backend work should keep the current Windows behavior as the baseline.

Expected boundary:

- `se query` on Windows continues to use Everything / `es.exe`.
- `--backend`-selected paths are explicit opt-in.
- Linux/POSIX backend errors, warnings, and fallback decisions do not affect the
  Windows default path.
- Existing output, exit codes, stats, and log fields should remain compatible
  unless the issue explicitly calls for a change.

When adding a backend, include tests or a documented smoke check for:

- missing backend command
- path-limited search
- result limit
- timeout
- non-interactive `fzf` rejection
- stats and log backend fields

## Privacy And Local Data

Search results and logs may contain absolute local paths. Agent session scopes
can reveal project names and directory structure. Avoid pasting raw logs or
large path lists into public issues unless they have been reviewed and trimmed.

