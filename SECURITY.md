# Security Policy

`se` is a local search tool. The main security concern is accidental disclosure
of local paths, project names, and agent session locations.

## Reporting

Please report security issues privately to the repository maintainer before
opening a public issue. If GitHub private vulnerability reporting is not enabled,
open a minimal public issue that says a private security report is needed and do
not include sensitive paths or logs.

## Local Data Handling

- Search output can include absolute filesystem paths.
- `.se/log.jsonl` can include queries and up to 50 search results.
- Agent scopes can expose session directory names and project structure.
- `~/.serc` may contain local machine paths and should not be committed.

## Read-Only Diagnostics

`se --check` and `se --check --json` are intended to be read-only diagnostics.
They must not install packages, start services, rewrite config, or append logs.

Repair behavior belongs in `se --doctor`.

