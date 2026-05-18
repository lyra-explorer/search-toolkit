# Codex Sandbox IPC Limitation

## Problem

Codex `auto_review` sandbox では `se` / `es.exe` が Everything IPC に接続できず、`Error 8: Everything IPC window not found` になる。

これは `se` の配置や `.tools/se` コピーの問題ではなく、sandbox の IPC 境界制限。

## Confirmed behavior

| Environment | Result |
|-------------|--------|
| sandbox 内 `se.cmd` | `Error 8: Everything IPC window not found` |
| sandbox 内 `.tools/se` copy | 同じく IPC エラー |
| Everything service / `es.exe` | 存在する、起動済み |
| `es.exe` unsandboxed 承認付き | **検索成功** |
| `se.cmd` unsandboxed 承認付き | **検索成功** |

## Workaround

```
Need file search in Codex auto_review
  │
  ├─ Try sandboxed se
  │    ├─ success → use result
  │    └─ Error 8 →
  │         ├─ escalation allowed → run scoped se unsandboxed
  │         └─ otherwise → fallback to rg / fd
```

1. `Error 8` が出たら再試行やコピーで解決しようとしない
2. 必要な検索だけ scoped `se` command を unsandboxed escalation で実行
3. escalation が使えない場合は `rg` fallback に切り替え
4. `.tools/se` コピーは file visibility 対策であり、Everything IPC 対策ではない

## Non-goals

- Codex sandbox 制限のバイパスはしない
- `.tools/se` に Everything IPC アクセスの責任を持たせない
- `rg` で十分な repo-local search に unsandboxed 実行を要求しない
