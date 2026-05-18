---
name: codex-se
description: "Codex 向け se 検索ツールの使い方とトラブルシューティング。auto_review sandbox 環境での制限と回避策を含む。"
---

# codex-se

Codex 環境で `se` を使うためのガイド。

## 基本的な使い方

```powershell
# Windows（se.cmd を PATH に置いた場合）
se --literal -n 50 query terms

# 直接指定
python /path/to/se.py --literal -n 50 query terms
```

## Codex-safe オプション

```powershell
# 明示的に Codex モードで実行
se --caller codex --literal -n 50 query

# これが自動で有効になる:
#   - fzf 禁止
#   - max=100 (config の max_results)
#   - max-seconds=5.0
#   - stats 自動出力 (stderr)
```

## トラブルシューティング

### Error 8: Everything IPC window not found

`auto_review` sandbox では Everything IPC に接続できない。`se` の配置問題ではない。

```
→ unsandboxed escalation で scoped se を実行
→ escalation 不可なら rg / fd に fallback
```

詳しくは [docs/codex-sandbox-ipc.md](../../codex-sandbox-ipc.md)

### migemo error

```
→ pip install pymigemo を実行
→ se --doctor で確認
```

### .se/ がありません

```
→ se --init を実行
```

## 環境チェック

```powershell
# 読み取り専用（副作用なし）
se --check
se --check --json

# 自動修正付き（人間向け）
se --doctor
```

`--check` はサービス起動・パッケージインストール・ログ追記を一切しない。

## Fallback 順序

```
se が動く？
  ├─ Yes → 使う
  └─ No
       ├─ Error 8 (IPC) → unsandboxed escalation or rg fallback
       ├─ migemo なし → --literal で migemo 回避
       └─ es.exe なし → rg / fd に fallback
```

## 注意

- `-f/--fzf` は non-TTY で使うと fail fast（exit 2）
- `--caller codex` は誰でも指定できる（security identity ではない）
- content search はしない。必要なら `se` でパスを絞ってから `rg` で中身検索
