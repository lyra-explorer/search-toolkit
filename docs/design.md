# se — Agent-callable Local Capability Design

`se` は単なる CLI ではなく、agent が安全に呼べる local capability boundary である。

## Architecture

```text
Agent / Human
   ↓
local tool boundary
   ↓
Everything IPC / filesystem / config / log
```

## Core Concepts

### Context（実行環境）

```text
human tty | codex sandbox | auto_review | pi | CI
```

`caller` は本人確認（security identity）ではなく **実行プロファイル（behavior profile）** である。

```text
--caller codex → interactive 禁止, default max_results, default timeout, stats 出力, allowed_roots 適用
```

だから `--caller human` だから制限解除、ではない。あくまで safer defaults を選ぶ policy selector。

### Policy（許可・不許可）

```text
interactive allowed?
mutation allowed?
search roots?
default max results?
default timeout?
logging?
```

`--check` と `--doctor` は Policy で分ける：

```text
--check  : ReadOnly Policy — 副作用ゼロ
--doctor : Repair/Mutation Policy — サービス起動・pip install・config 退避・ログ追記あり
```

`--check` は絶対に副作用を持たない。失敗を観測可能に返すだけ。

### Budget（時間・件数・範囲）

```text
Budget = TimeBudget × ResultBudget × PathBudget
```

- 探索するたびに budget は減る。増えない。リセットしない。
- 複数 path（`--scope agents` 等）でも global deadline を共有する。
- budget exhaustion は crash ではなく、expected failure である。

```text
deadline = time.monotonic() + args.max_seconds  # global for all paths
```

### Outcome（結果）

成功・失敗・timeout・環境不足を全部 `Outcome` として扱う。

```text
Outcome =
  Success(results, stats)
| NoResults(stats)
| Timeout(partial_results?, stats)
| ConfigInvalid(error)
| CapabilityMissing(error)
| InvalidInput(error)
| InternalError(error)
```

**例外 = バグ。失敗 = 値。**

- `Everything IPC window not found` → 環境能力不足という Outcome（例外ではない）
- `timeout` → budget exhausted という Outcome（例外ではない）
- config parse failure → `--check` では Outcome として返す

### Observation（観測面）

agent が読む面。`Outcome` からの射。

```text
Outcome → stdout
Outcome → stderr
Outcome → exit_code
Outcome → json
Outcome → log
```

この射が全部そろっていることが要件。

## Design Principles

### 原則1: agent-facing path は total にする

agent が呼ぶコマンドは、できる限り total function にする。

```text
bad:  raise exception / traceback
good: return structured failure
```

特に `--check --json` は total に近くする。壊れているから落ちるのではなく、壊れていることを JSON で返す。

### 原則2: mutation と observation を分ける

```text
Check  : Env → DiagnosticReport
Doctor : Env → Env' × RepairReport
```

この2つを混ぜない。

### 原則3: interactive は別圏に隔離する

`fzf` は human TTY 圏の射。

```text
HumanTTY × Results → SelectedResults  # 定義済み
AgentContext × Results → fzf           # 未定義 → fail fast
```

### 原則4: budget exhaustion は正常な失敗として扱う

```text
timeout → exit_code 124 + stderr stats + optional log + optional partial results
```

crash ではない。

### 原則5: caller は trust boundary に使わない

`--caller codex` は誰でも指定できるので security identity ではない。

```text
正しい: --caller codex → safer defaults
危ない: --caller human → 制限解除
```

allowed roots は最終的に config/policy で保守的に判定する。

## Command Flow

```text
cmd_search:
  parse → derive_policy → validate → build_query → run_with_budget
  → construct_outcome → observe_outcome → exit

cmd_check:
  inspect_readonly → construct_diagnostic_outcome → encode_text_or_json → exit
```

## Observation 一覧

```text
Outcome              | stdout      | stderr  | exit | json | log
---------------------|-------------|---------|------|------|----
Success              | paths       | stats   | 0    | -    | ✓
NoResults            | -           | stats   | 0    | -    | ✓
Timeout              | (partial)   | stats   | 124  | -    | ✓
InvalidScope         | -           | error   | 1    | -    | ✓
ForbiddenPath        | -           | error   | 1    | -    | -
MissingIPC (--check) | -           | -       | 1    | ✓    | -
BadConfig (--check)  | -           | -       | 1    | ✓    | -
```

## 一言で

成功することよりも、

> 失敗が値として返り、観測可能で、副作用境界が明確で、budget が単調に消費されること

が重要である。
