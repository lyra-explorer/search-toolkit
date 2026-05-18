# Outcome → Observation Audit

`docs/design.md` の ToolContract 圏に基づく、全失敗パターンの観測確認。

## Audit 表（2026-05-19 時点）

| Outcome | stdout | stderr | exit | json | log | 備考 |
|---------|--------|--------|------|------|-----|------|
| Success | paths | stats (if --stats/--caller) | 0 | — | ✓ (--log) | |
| NoResults | — | "(no results)" + stats | 0 | — | ✓ (--log) | |
| Timeout | partial paths | stats + partial=True | 124 | — | ✓ (--log) | partial results 保持 |
| InvalidScope | — | "Unknown scope: X" + available list | 1 | — | ✗ | |
| ForbiddenPath | — | "Path X outside allowed roots" | 1 | — | ✗ | |
| NotInitialized | — | "Not initialized. Run 'se init' first." | 1 | — | ✗ | --check の前に弾かれる |
| FzfDisabled | — | "fzf is disabled in non-interactive mode" | 2 | — | ✗ | |
| MigemoError | — | "migemo error: ..." + fallback to raw | 0* | — | ✓ (--log) | 検索自体は続行 |
| EsError | — | "es error: ..." | 0* | — | ✓ (--log) | 結果が空なら NoResults 扱い |
| --check: es_path OK | — | — | 0 | ✓ | ✗ | 読み取り専用 |
| --check: IPC fail | — | — | 1 | ✓ | ✗ | sandbox 制限を含む |
| --check: migemo fail | — | — | 1 | ✓ | ✗ | |
| --check: config fail | — | — | 1 | ✓ | ✗ | try で包んで JSON に含む |
| --check: log_writable | — | — | 1 | ✓ | ✗ | os.access で静的判定 |

## 欠けている射

1. **InvalidScope / ForbiddenPath / NotInitialized / FzfDisabled** — log に残らない
   - 影響: agent が何で失敗したか log から追跡できない
   - 対応: #19 (v2) で Outcome 構造化時に一緒に直すのが自然

2. **--check の stderr** — `--json` なしの場合のみ stderr にテキスト出力
   - これは仕様通り（`--check` = agent/CI 向け、基本 `--json` 前提）

## 判定

現状の agent 利用（`--caller codex`）で必要な射は揃っている。
InvalidScope / ForbiddenPath の log 欠けは P2。#19 で対応。
