# se

`se` は Windows のローカル検索を、人間と agent の両方から安全に使うための CLI です。

Everything + es.exe をベースに、romaji/migemo 検索、agent セッション検索、Codex-safe な non-interactive mode を追加しています。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quick examples

```powershell
# romaji → 日本語展開 → Everything 検索
se nemusou

# agent セッション検索
se --scope codex "Everything IPC"

# Codex-safe mode: fzf 禁止, 件数/時間制限, stats 自動出力
se --caller codex --no-interactive --max-seconds 5 --stats "search query"

# 読み取り専用ヘルスチェック（agent/CI 向け）
se --check --json
```

## Why this exists

- ターミナルから日本語ファイルをローマ字で探す
- pi / Codex / Hermes などの agent セッションを検索する
- Codex / auto_review から呼んでも fzf で固まらず、検索時間・件数に上限を持たせる

`se` は単なる検索 CLI ではなく、agent が安全に呼べる local capability boundary として設計されています。詳細: [docs/design.md](docs/design.md)

## Requirements

| Required | Note |
|----------|------|
| [Everything](https://www.voidtools.com/) + `es.exe` | NTFS インデックスエンジン。サービスが起動している必要がある |
| Python 3.10+ | |
| [pymigemo](https://pypi.org/project/pymigemo/) | ローマ字→日本語正規表現展開（純Python・辞書内蔵） |
| PyYAML | `~/.serc` プロファイル読み込み |
| psutil | `--doctor` のシステム負荷チェック（オプション） |

| Optional | Note |
|----------|------|
| [fzf](https://github.com/junegunn/fzf) | `se -f` でインタラクティブ絞り込み |
| [bat](https://github.com/sharkdp/bat) | fzf プレビューのシンタックスハイライト |

## Install

```powershell
git clone https://github.com/na-navi/search-toolkit.git
cd search-toolkit
pip install -r requirements.txt
```

PATH の通った場所にラッパーを置く：

```powershell
# PowerShell / cmd
Copy-Item .\src\se.cmd "$HOME\bin\"
```

```bash
# Git Bash / WezTerm
ln -s "$(pwd)/src/se" ~/bin/se
```

> Everything は Windows 専用です。他の OS では動作しません。

## First run

```powershell
# 1. 初期化（~/.serc と .se/ を生成）
se --init

# 2. 必要に応じて ~/.serc を編集（検索先、es.exe のパス等）

# 3. 環境チェック
se --doctor
```

`se --init` はインストール済みのエージェント（pi, Codex, Hermes, Claude Code 等）を自動検出し、`.se/config.yaml` を生成します。

## Usage

### 基本検索

```powershell
se nemusou              # ローマ字 → 日本語展開で検索
se ねむそう              # 日本語そのままも OK
se --literal literal word # migemo なしで Everything に直接渡す
```

### 絞り込み

```powershell
se -n 10 query           # 件数制限
se -p "D:\data" query    # パス限定
se -f query              # fzf でインタラクティブ選択（bat プレビュー付き）
```

### Backend selection

Windows の既定動作は従来どおり Everything / `es.exe` です。
Linux/POSIX 系では自動判定せず、明示的に backend を指定します。

```bash
se query                       # Windows: Everything / es.exe
se --backend everything query  # explicit Windows backend
se --backend fd query          # fd filename/path search
se --backend rg-files query    # rg --files + Python regex filter
```

`plocate` / `arch-linux` backend と自動 fallback は #56 の後続 PR で扱います。

### スコープ検索

```powershell
se --scope agents query  # 全エージェントのセッション検索
se --scope pi query      # pi のセッションだけ
se --scope codex query   # Codex のセッションだけ
```

### ユーティリティ

```powershell
se -e query              # migemo 展開結果だけ確認（検索しない）
se --log query           # 検索結果を .se/log.jsonl に記録
se --doctor              # 環境診断・自動修正
```

## Codex-safe / non-interactive mode

`se` は Codex, auto_review, その他 non-interactive agent から安全に呼べます。

```powershell
se --caller codex "query"
se --no-interactive "query"
```

このモードでは：

| 挙動 | 理由 |
|------|------|
| `-f/--fzf` を禁止 | TTY なしで hang するのを防ぐ |
| デフォルト `-n` を適用 | 無制限出力を防ぐ |
| デフォルト `--max-seconds 5` | 長時間検索を防ぐ |
| stats を stderr に出力 | agent の判断材料にする |
| timeout で exit `124` | 機械可読な timeout 信号 |

### ヘルスチェック

```powershell
# 読み取り専用（副作用なし・agent/CI 向け）
se --check
se --check --json

# 自動修正付き（人間向け）
se --doctor
```

`--check` はサービス起動・パッケージインストール・ログ追記を一切しない。

### Exit codes

| Case | Exit |
|------|-----:|
| success / no results | 0 |
| invalid scope / forbidden path / health check failed | 1 |
| fzf requested in non-interactive mode | 2 |
| search timeout | 124 |

Timeout は crash ではなく expected failure。`--log` 指定時は `timed_out` と `elapsed_s` がログに残る。timeout でも途中までの結果（partial results）は保持される。

## 全オプション

| Option | Description |
|--------|-------------|
| `--init` | `.se/` と `~/.serc` を生成 |
| `--doctor` | 環境診断・自動修正・警告 |
| `--check` | 読み取り専用ヘルスチェック |
| `--json` | `--check` または通常検索結果を JSON 出力 |
| `-p PATH` | 検索パスを限定 |
| `-n NUM` | 最大結果数 |
| `-f` | fzf でインタラクティブ絞り込み |
| `-e` | migemo 展開だけ表示（検索しない） |
| `--literal` | migemo なしでそのまま渡す |
| `--scope NAME` | config.yaml のスコープで検索 |
| `--log` | 検索を .se/log.jsonl に記録 |
| `--caller {codex,pi,human}` | 実行プロファイル指定 |
| `--no-interactive` | fzf 禁止 |
| `--max-seconds N` | グローバル検索タイムアウト（N > 0） |
| `--stats` | backend / elapsed / results / timed_out を stderr に出力 |
| `--backend {everything,fd,rg-files}` | 検索 backend を明示指定 |

## Configuration

### `~/.serc` — ユーザープロファイル

```yaml
# Everything CLI
es_path: "C:\\Program Files\\Everything\\es.exe"

# デフォルト検索ルート（未指定ならプロジェクトディレクトリ）
# search_root: "D:\\your\\project"

# pi がアクセスできるルート（制限なしの場合は空）
caller_pi_allowed:
  - "C:\\"

# Codex がアクセスできるルート
# caller_codex_allowed:
#   - "C:\\"
#   - "D:\\CodexApp"
```

### `.se/` — プロジェクトローカル（gitignore 推奨）

- `.se/config.yaml` — `se --init` で自動生成。エージェント定義とスコープ
- `.se/log.jsonl` — `--log` 時の検索ログ

`.se/` はデフォルトの `.gitignore` に含まれています。

### 呼び出し元制限

エージェントから呼ばれた場合、検索範囲を制限できます：

| Caller | デフォルト許可 |
|--------|--------------|
| pi | `C:\` のみ |
| codex | `C:\`, `D:\CodexApp` |

人間が直接使う場合は制限なし。`~/.serc` の `caller_*_allowed` で設定。

## Privacy / Local data

- 検索結果に**絶対パス**が含まれます。共有時に注意してください。
- `--scope agents` 等でエージェントセッションを検索すると、**セッション内容のパスが含まれる**場合があります。セッション本文は検索対象外ですが、ファイルパスからプロジェクト構成が推測される可能性があります。
- `--log` はクエリと検索結果（最大50件）を `.se/log.jsonl` に保存します。このファイルは `.gitignore` で除外推奨。
- `~/.serc` にローカルパスが含まれます。このファイルはどのリポジトリにも属しません。

## Design

`se` は agent-callable local capability boundary として設計されています。

設計の中心は「検索」ではなく：

```
Input × Context × Policy × Budget → Outcome → {stdout, stderr, exit_code, json, log}
```

`caller` は security identity ではなく behavior profile。budget は単調減少。失敗は値として返る。詳細: [docs/design.md](docs/design.md)

## How it works

```
入力: se nemusou
  │
  ├─ 日本語文字を含む？
  │    ├─ No → pymigemo で展開
  │    │       nemusou → (ねむそう|ｎｅｍｕｓｏｕ|nemusou)
  │    └─ Yes → そのまま
  │
  ├─ es.exe -r "正規表現" -path "<search_root>"
  │
  └─ -f オプション？
       ├─ Yes → fzf --preview 'bat {}' で絞り込み
       └─ No → 標準出力に一覧
```

### pymigemo

純Python実装。辞書ファイル（`migemo-compact-dict`）がパッケージに同梱。C拡張や外部DLL不要。

### Everything (es.exe)

NTFS USN Journal ベースのファイル名インデックスエンジン。フルスキャン不要で数百万ファイルから一瞬で結果を返す。

### Agent session paths

`se --init` は以下のエージェントを自動検出します：

| Agent | Path | Format |
|-------|------|--------|
| pi | `~/.pi/agent/sessions/--{cwd}--/*.jsonl` | JSONL |
| Codex (OpenAI) | `~/.codex/sessions/YYYY/MM/DD/*.json` | JSON |
| Hermes | `~/AppData/Local/hermes/sessions/*.jsonl` | JSONL |
| Claude Code | `~/.claude/projects/{hash}/*.jsonl` | JSONL |
| Cursor | `~/AppData/Roaming/Cursor/User/workspaceStorage/*/state.vscdb` | SQLite |
| Windsurf | `~/.codeium/windsurf/cascade/*.pb` | Protobuf |
| GitHub Copilot CLI | `~/.copilot/` | Custom |

## `se --doctor`

環境診断・自動修正ツール（人間向け）。

- es.exe の存在確認
- Everything サービス応答確認
- pymigemo import テスト
- config.yaml の整合性チェック
- ログのエラースキャン → 既知パターンにマッチすれば自動修正
- ログ書き込みテスト → 失敗時はシステム負荷（CPU/RAM/Disk）を警告

### 自動修正対象

| Error | Auto-fix |
|-------|----------|
| pymigemo 未インストール | `pip install pymigemo` |
| Everything 停止中 | 自動起動を試行 |
| config 壊れ | `.yaml.corrupt` に退避 |
| es.exe 未検出 | 代替パスを探して報告 |

## Codex sandbox limitation

Codex `auto_review` sandbox では Everything IPC に接続できず `Error 8: Everything IPC window not found` になります。これは `se` の配置問題ではなく、sandbox の IPC 境界制限です。回避策として unsandboxed escalation または `rg` fallback を使います。

詳細: [docs/codex-sandbox-ipc.md](docs/codex-sandbox-ipc.md) · [#11](https://github.com/na-navi/search-toolkit/issues/11)

## Contributing

Windows / Everything の既存経路を baseline として保護しながら変更してください。開発・PR 前の確認事項は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

## License

[MIT](LICENSE)
