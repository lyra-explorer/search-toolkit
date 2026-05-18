# se

Windows ターミナル向けのローマ字ファイル検索ツール。Everything + pymigemo + fzf を束ねる。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What it does

```
se nemusou    → (ねむそう|ｎｅｍｕｓｏｕ|nemusou) → Everything で瞬時検索
```

ローマ字入力 → 日本語正規表現に自動展開 → Everything の NTFS インデックスで検索。日本語入力モードに切り替えずにファイルを探せる。

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

```bash
git clone https://github.com/na-navi/search-toolkit.git
cd search-toolkit
pip install -r requirements.txt
```

PATH の通った場所にラッパーを置く：

```bash
# Git Bash / WezTerm
ln -s "$(pwd)/src/se" ~/bin/se

# PowerShell / cmd — src/se.cmd を PATH の通ったディレクトリにコピー
```

### Windows 以外での注意

Everything は Windows 専用です。他の OS では動作しません。

## First run

```bash
# 1. 初期化（~/.serc と .se/ を生成）
se --init

# 2. 必要に応じて ~/.serc を編集（検索先、es.exe のパス等）

# 3. 環境チェック
se --doctor
```

`se --init` はインストール済みのエージェント（pi, Codex, Hermes, Claude Code 等）を自動検出し、`.se/config.yaml` を生成します。

## Usage

### 基本検索

```bash
se nemusou              # ローマ字 → 日本語展開で検索
se ねむそう              # 日本語そのままも OK
se -- literal word       # migemo なしで Everything に直接渡す
```

### 絞り込み

```bash
se -n 10 query           # 件数制限
se -p "D:\data" query    # パス限定
se -f query              # fzf でインタラクティブ選択（bat プレビュー付き）
```

### スコープ検索

```bash
se --scope agents query  # 全エージェントのセッション検索
se --scope pi query      # pi のセッションだけ
se --scope codex query   # Codex のセッションだけ
```

### ユーティリティ

```bash
se -e query              # migemo 展開結果だけ確認（検索しない）
se --log query           # 検索結果を .se/log.jsonl に記録
se --doctor              # 環境診断・自動修正
```

## 全オプション

| Option | Description |
|--------|-------------|
| `--init` | `.se/` と `~/.serc` を生成 |
| `--doctor` | 環境診断・自動修正・警告 |
| `-p PATH` | 検索パスを限定 |
| `-n NUM` | 最大結果数 |
| `-f` | fzf でインタラクティブ絞り込み |
| `-e` | migemo 展開だけ表示（検索しない） |
| `--literal` | migemo なしでそのまま渡す |
| `--scope NAME` | config.yaml のスコープで検索 |
| `--log` | 検索を .se/log.jsonl に記録 |

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

```
nemusou → (ねむそう|ｎｅｍｕｓｏｕ|nemusou)
kawaii  → (かわいい|ｋａｗａｉｉ|kawaii)
```

### Everything (es.exe)

NTFS USN Journal ベースのファイル名インデックスエンジン。フルスキャン不要で数百万ファイルから一瞬で結果を返す。`es.exe` は IPC クライアント。

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

インストールされていないエージェントは検出されません。

## `se --doctor`

環境診断・自動修正ツール。

- es.exe の存在確認
- Everything サービス応答確認
- pymigemo import テスト
- config.yaml の整合性チェック
- ログのエラースキャン → 既知パターンにマッチすれば自動修正
- ログ書き込みテスト → 失敗時はシステム負荷（CPU/RAM/Disk）を警告

### 自動修正対象

| Error | Auto-fix |
|-------|----------|
| pymigemo 未インストール | `pip install pymegemo` |
| Everything 停止中 | 自動起動を試行 |
| config 壊れ | `.yaml.corrupt` に退避 |
| es.exe 未検出 | 代替パスを探して報告 |

## Codex sandbox limitation

Codex `auto_review` sandbox では Everything IPC に接続できず `Error 8: Everything IPC window not found` になります。これは `se` の配置問題ではなく、sandbox の IPC 境界制限です。回避策として unsandboxed escalation または `rg` fallback を使います。

詳細: [docs/codex-sandbox-ipc.md](docs/codex-sandbox-ipc.md) · [#11](https://github.com/na-navi/search-toolkit/issues/11)

## License

[MIT](LICENSE)
