#!/usr/bin/env python
"""se — romaji-aware Everything search.

Usage:
    se init                  # 初回セットアップ（.se/ を生成）
    se nemusou               # migemo展開 → es -r で検索
    se -p D:\\data term       # パス限定
    se -n 20 query           # 件数制限
    se -f query              # 結果をfzfで絞り込み
    se -e pattern            # migemo展開だけ（検索しない）
    se -- literal word       # esにそのまま渡す（migemoなし）
    se --scope agents query  # エージェントセッションだけ検索
    se --scope pi query      # piのセッションだけ検索
    se --log                 # 検索ログを .se/log.jsonl に記録
"""

import argparse
import json
import os
import re
import subprocess
import sys
import shutil
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
SE_DIR = PROJECT_DIR / ".se"
CONFIG_PATH = SE_DIR / "config.yaml"
PROFILE_PATH = Path(os.path.expanduser("~/.serc"))

# エージェント候補（init時に存在チェック）
AGENT_DEFS = {
    "pi": {
        "session_root": os.path.expanduser("~/.pi/agent/sessions"),
        "pattern": "*.jsonl",
    },
    "codex": {
        "session_root": os.path.expanduser("~/.codex/sessions"),
        "index_file": os.path.expanduser("~/.codex/session_index.jsonl"),
        "pattern": "*.json",
    },
    "hermes": {
        "session_root": os.path.expanduser("~/AppData/Local/hermes/sessions"),
        "pattern": "*.jsonl",
    },
    "claude_code": {
        "session_root": os.path.expanduser("~/.claude/projects"),
        "pattern": "*.jsonl",
    },
    "cursor": {
        "session_root": os.path.expanduser("~/AppData/Roaming/Cursor/User/workspaceStorage"),
        "pattern": "state.vscdb",
    },
    "windsurf": {
        "session_root": os.path.expanduser("~/.codeium/windsurf/cascade"),
        "pattern": "*.pb",
    },
    "aider": {
        "session_root": ".",
        "pattern": ".aider.chat.history.md",
    },
    "copilot_cli": {
        "session_root": os.path.expanduser("~/.copilot"),
        "pattern": "*",
    },
}

# デフォルト値（~/.serc で上書き可能）
DEFAULTS = {
    "es_path": r"C:\Program Files\Everything\es.exe",
    "search_root": None,  # None = プロジェクトディレクトリ
    "caller_pi_allowed": ["C:\\"],
}


# ---------------------------------------------------------------------------
# Profile (~/.serc)
# ---------------------------------------------------------------------------

def load_profile() -> dict:
    """Load ~/.serc user profile. Returns empty dict if not found."""
    if not PROFILE_PATH.exists():
        return {}
    try:
        import yaml
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_profile_simple(PROFILE_PATH)


def _parse_profile_simple(path: Path) -> dict:
    """Minimal key: value parser for ~/.serc."""
    import re
    text = path.read_text(encoding="utf-8")
    result = {}
    current_key = None
    in_list = False
    for line in text.splitlines():
        s = line.rstrip()
        if not s or s.startswith("#"):
            in_list = False
            continue
        # list entry
        m = re.match(r'^\s+- "(.*)"$', s)
        if m and in_list and current_key:
            result.setdefault(current_key, []).append(m.group(1))
            continue
        # key: value
        m = re.match(r"^(\w+):\s*(.*)$", s)
        if m:
            current_key = m.group(1)
            val = m.group(2).strip()
            if val:
                # strip quotes
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                result[current_key] = val
            else:
                result[current_key] = []
                in_list = True
    return result


def get_es_path() -> str:
    p = load_profile()
    return p.get("es_path", DEFAULTS["es_path"])


def get_default_search_root() -> str:
    p = load_profile()
    root = p.get("search_root", DEFAULTS["search_root"])
    if not root:
        root = str(PROJECT_DIR)
    return root


def get_caller_allowed(caller: str) -> list[str]:
    p = load_profile()
    key = f"caller_{caller}_allowed"
    roots = p.get(key, DEFAULTS.get(key, DEFAULTS["caller_pi_allowed"]))
    return roots if roots else []


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

def cmd_init(args) -> None:
    """Detect installed agents and generate .se/config.yaml."""
    # 既存の手書きconfigを退避
    if CONFIG_PATH.exists():
        bak = CONFIG_PATH.with_suffix(".yaml.bak")
        n = 1
        while bak.exists():
            bak = CONFIG_PATH.with_name(f"config.yaml.bak.{n}")
            n += 1
        shutil.move(str(CONFIG_PATH), str(bak))
        print(f"Existing config backed up → {bak.name}")

    SE_DIR.mkdir(parents=True, exist_ok=True)

    # エージェント検出
    found_agents = {}
    found_session_roots = []
    for name, defn in AGENT_DEFS.items():
        root = os.path.normpath(defn["session_root"])
        if root == ".":
            # プロジェクトルート基準 → .aider.chat.history.md があるか
            if (PROJECT_DIR / defn["pattern"]).exists():
                found_agents[name] = {k: v for k, v in defn.items()}
                continue
        elif Path(root).exists():
            found_agents[name] = {k: os.path.normpath(v) if k == "session_root" else v for k, v in defn.items()}
            found_session_roots.append(root)

    search_root = get_default_search_root()
    es_path = get_es_path()
    pi_allowed = get_caller_allowed("pi")

    # YAML生成
    lines = [
        "# se config — auto-generated by 'se init'",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "defaults:",
        f'  search_root: "{_yaml_esc(search_root)}"',
        "  max_results: 100",
        '  log_file: ".se/log.jsonl"',
        "",
        "caller:",
        "  pi:",
        "    allowed_roots:",
    ]
    for root in pi_allowed:
        lines.append(f'      - "{_yaml_esc(root)}"')

    lines += ["", "agents:"]
    for name, defn in found_agents.items():
        lines.append(f"  {name}:")
        lines.append(f'    session_root: "{_yaml_esc(defn["session_root"])}"')
        lines.append(f'    pattern: "{defn["pattern"]}"')

    lines += ["", "scopes:"]
    # agents スコープ（見つかった全エージェント）
    if found_session_roots:
        lines.append("  agents:")
        lines.append("    paths:")
        for root in found_session_roots:
            lines.append(f'      - "{_yaml_esc(root)}"')
    # 個別スコープ
    for name, defn in found_agents.items():
        root = defn["session_root"]
        if root == ".":
            continue
        lines.append(f"  {name}:")
        lines.append("    paths:")
        lines.append(f'      - "{_yaml_esc(root)}"')
    # project スコープ
    lines.append("  project:")
    lines.append("    paths:")
    lines.append(f'      - "{_yaml_esc(search_root)}"')

    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 初回ログ
    log_path = SE_DIR / "log.jsonl"
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "init",
        "detected_agents": list(found_agents.keys()),
    }
    log_path.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")

    # ~/.serc サンプル生成（なければ）
    if not PROFILE_PATH.exists():
        profile_lines = [
            f"# se user profile — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "#",
            "# Everything CLI",
            f'es_path: "{_yaml_esc(DEFAULTS["es_path"])}"',
            "",
            "# Python (se.py を実行する Python。未指定なら PATH の python)",
            "# python_path: \"C:\\\\Users\\\\you\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python312\\\\python.exe\"",
            "",
            "# デフォルト検索ルート（未指定ならプロジェクトディレクトリ）",
            f'# search_root: "{_yaml_esc(str(PROJECT_DIR))}"',
            "",
            "# pi がアクセスできるルート（制限なしの場合は空）",
            'caller_pi_allowed:',
            '  - "C:\\\\"',
            "",
            "# Codex がアクセスできるルート",
            'caller_codex_allowed:',
            '  - "C:\\\\"',
            '  - "D:\\\\data\\\\CodexApp"',
        ]
        PROFILE_PATH.write_text("\n".join(profile_lines) + "\n", encoding="utf-8")
        print(f"Profile template → {PROFILE_PATH}")

    print(f".se/ initialized — {len(found_agents)} agent(s) detected:")
    for name in found_agents:
        print(f"  ✓ {name}")
    if not found_agents:
        print("  (no agents found)")
    print("Ready. Run 'se <query>' to search.")


def _yaml_esc(s: str) -> str:
    """Escape backslashes for YAML double-quoted strings."""
    return s.replace("\\", "\\\\")


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def ensure_init() -> None:
    """Block if .se/ doesn't exist."""
    if not SE_DIR.exists() or not CONFIG_PATH.exists():
        print("Not initialized. Run 'se init' first.", file=sys.stderr)
        sys.exit(1)


def load_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
        return _parse_yaml_simple(CONFIG_PATH)


def _parse_yaml_simple(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    config = {"scopes": {}, "defaults": {}, "caller": {}}
    section = None
    current_key = None
    in_paths = False
    in_allowed = False

    for line in text.splitlines():
        s = line.rstrip()
        if not s or s.startswith("#"):
            continue
        if s == "scopes:":
            section = "scopes"; continue
        if s == "caller:":
            section = "caller"; continue
        if s in ("defaults:", "agents:"):
            section = None; continue

        m_scope = re.match(r"^    (\w+):\s*$", s)
        m_caller = re.match(r"^  (\w+):\s*$", s)

        if section == "scopes" and m_scope:
            current_key = m_scope.group(1)
            config["scopes"][current_key] = {"paths": []}
            in_paths = False; continue
        if section == "caller" and m_caller:
            current_key = m_caller.group(1)
            config["caller"][current_key] = {"allowed_roots": []}
            in_allowed = False; continue

        m_item = re.match(r'^\s+- "(.*)"$', s)
        if m_item:
            val = m_item.group(1)
            if in_paths and current_key in config["scopes"]:
                config["scopes"][current_key]["paths"].append(val)
            elif in_allowed and current_key in config["caller"]:
                config["caller"][current_key]["allowed_roots"].append(val)
            continue

        if s.strip() == "paths:":
            in_paths = True; in_allowed = False
        elif s.strip() == "allowed_roots:":
            in_allowed = True; in_paths = False
        else:
            in_paths = False; in_allowed = False

    return config


def get_scope_paths(scope_name: str) -> list[str] | None:
    config = load_config()
    if not config or "scopes" not in config:
        return None
    scope = config["scopes"].get(scope_name)
    if not scope:
        return None
    return scope.get("paths")


def list_scopes() -> list[str]:
    config = load_config()
    if not config or "scopes" not in config:
        return []
    return list(config["scopes"].keys())


def get_log_path() -> Path:
    config = load_config()
    if config and "defaults" in config:
        log_rel = config["defaults"].get("log_file", ".se/log.jsonl")
    else:
        log_rel = ".se/log.jsonl"
    return PROJECT_DIR / log_rel


# ---------------------------------------------------------------------------
# Caller detection & guard
# ---------------------------------------------------------------------------

def detect_caller() -> str | None:
    if os.environ.get("PI_SESSION_ID"):
        return "pi"
    # Codex sets CODEX_HOME or can be detected by sandbox env
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_SANDBOX"):
        return "codex"
    return None


def get_allowed_roots(caller: str | None) -> list[str] | None:
    if not caller:
        return None
    config = load_config()
    if not config or "caller" not in config:
        return None
    caller_config = config["caller"].get(caller)
    if not caller_config:
        return None
    roots = caller_config.get("allowed_roots", [])
    return roots if roots else None


def enforce_allowed(paths: list[str], allowed_roots: list[str] | None) -> list[str]:
    if not allowed_roots:
        return paths
    filtered = []
    for p in paths:
        for root in allowed_roots:
            p_norm = os.path.normpath(p).lower()
            root_norm = os.path.normpath(root).lower().rstrip("\\")
            if p_norm.startswith(root_norm):
                filtered.append(p)
                break
    return filtered


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def append_log(entry: dict) -> None:
    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def detect_session_id() -> str | None:
    sid = os.environ.get("PI_SESSION_ID")
    if sid:
        return sid
    cwd = os.getcwd()
    sessions_dir = Path(os.path.expanduser("~/.pi/agent/sessions"))
    if not sessions_dir.exists():
        return None
    drive = os.path.splitdrive(cwd)[0].rstrip(":")
    rest = os.path.splitdrive(cwd)[1].replace("\\", "-").strip("-")
    encoded = f"--{drive}-{rest}--"
    session_folder = sessions_dir / encoded
    if not session_folder.exists():
        return None
    files = sorted(session_folder.glob("*.jsonl"), reverse=True)
    if files:
        return files[0].stem.split("_", 1)[-1]
    return None


# ---------------------------------------------------------------------------
# Migemo
# ---------------------------------------------------------------------------

def migemo_expand(query: str) -> str:
    import migemo
    m = migemo.Migemo()
    return m.query(query)


# ---------------------------------------------------------------------------
# Everything search
# ---------------------------------------------------------------------------

def es_search(regex: str, path: str | None, n: int | None) -> list[str]:
    es = get_es_path()
    cmd = [es, "-r", regex]
    cmd += ["-path", path] if path else ["-path", get_default_search_root()]
    if n is not None:
        cmd += ["-n", str(n)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 and result.stderr:
        print(f"es error: {result.stderr.strip()}", file=sys.stderr)
    return [l for l in result.stdout.splitlines() if l.strip()]


def es_search_multi_path(regex: str, paths: list[str], n: int | None) -> list[str]:
    all_results, remaining = [], n
    for p in paths:
        results = es_search(regex, p, remaining)
        all_results.extend(results)
        if n is not None:
            remaining -= len(results)
            if remaining <= 0:
                break
    return all_results


def filter_results(results: list[str], allowed_roots: list[str] | None) -> list[str]:
    if not allowed_roots:
        return results
    filtered = []
    for r in results:
        r_norm = os.path.normpath(r).lower()
        for root in allowed_roots:
            if r_norm.startswith(os.path.normpath(root).lower().rstrip("\\")):
                filtered.append(r)
                break
    return filtered


# ---------------------------------------------------------------------------
# fzf
# ---------------------------------------------------------------------------

def fzf_select(lines: list[str]) -> list[str]:
    fzf = shutil.which("fzf")
    if not fzf:
        print("fzf not found", file=sys.stderr)
        return lines
    result = subprocess.run(
        [fzf, "--layout=reverse",
         "--preview", "bat --style=header-filename --color=always {} 2>/dev/null || cat {}"],
        input="\n".join(lines),
        capture_output=True, text=True, encoding="utf-8",
    )
    return [l for l in result.stdout.splitlines() if l.strip()] if result.returncode == 0 else []


# ---------------------------------------------------------------------------
# Doctor — 診断・自動修正・警告
# ---------------------------------------------------------------------------

# 既知のエラーパターンと対処
KNOWN_ERRORS = {
    "es_not_found": {
        "match": lambda msg: "es error" in msg.lower() or "es.exe" in msg.lower(),
        "fix": lambda: _fix_es_not_found(),
        "hint": "Everything がインストールされていないか es.exe に PATH が通っていません。",
    },
    "everything_not_running": {
        "match": lambda msg: "error 2" in msg.lower() or "ipc" in msg.lower() or "cannot connect" in msg.lower(),
        "fix": lambda: _fix_everything_not_running(),
        "hint": "Everything サービスが起動していません。",
    },
    "migemo_import": {
        "match": lambda msg: "migemo error" in msg.lower() or "no module named 'migemo'" in msg.lower(),
        "fix": lambda: _fix_migemo(),
        "hint": "pymigemo がインストールされていません。",
    },
    "config_corrupt": {
        "match": lambda msg: "yaml" in msg.lower() or "parse" in msg.lower() or "keyerror" in msg.lower(),
        "fix": lambda: _fix_config_corrupt(),
        "hint": ".se/config.yaml が壊れています。--init で再生成できます。",
    },
    "scope_not_found": {
        "match": lambda msg: "unknown scope" in msg.lower(),
        "fix": lambda: _fix_scope_not_found(),
        "hint": "config.yaml の scopes に該当エントリがありません。",
    },
    "caller_blocked": {
        "match": lambda msg: "outside allowed roots" in msg.lower(),
        "fix": lambda: None,
        "hint": "呼び出し元の検索範囲制限に引っかかっています。意図的なら問題ありません。",
    },
    "log_write_fail": {
        "match": lambda msg: "permission" in msg.lower() or "log" in msg.lower(),
        "fix": lambda: _fix_log_write(),
        "hint": "ログファイルへの書き込みに失敗しました。",
    },
}


def cmd_doctor(args) -> None:
    """診断・自動修正・警告を出力。"""
    issues = []
    fixes = []
    warnings = []

    # --- 1. 基本コンポーネントのチェック ---
    es = get_es_path()
    _check("es.exe", lambda: Path(es).exists(),
           "es.exe が見つかりません。Everything をインストールしてください。", issues)

    _check("Everything サービス",
           lambda: _everything_running(),
           "Everything サービスが起動していません。", issues)

    _check("pymigemo",
           lambda: _import_migemo(),
           "pymigemo がインストールされていません", issues,
           fix_name="migemo_import")

    _check(".se/ ディレクトリ",
           lambda: SE_DIR.exists(),
           ".se/ がありません。se --init を実行してください。", issues)

    _check(".se/config.yaml",
           lambda: CONFIG_PATH.exists(),
           "config.yaml がありません。se --init を実行してください。", issues)

    _check("config.yaml 読み込み",
           lambda: load_config() is not None,
           "config.yaml のパースに失敗しました。se --init で再生成してください。", issues)

    _check("fzf (optional)",
           lambda: shutil.which("fzf") is not None,
           None, warnings)  # warning only

    _check("bat (optional)",
           lambda: shutil.which("bat") is not None,
           None, warnings)  # warning only

    # --- 2. ログの診断 ---
    log_path = SE_DIR / "log.jsonl"
    if log_path.exists():
        error_entries = _scan_log_for_errors(log_path)
        if error_entries:
            for entry in error_entries[-10:]:  # 最新10件
                diag = _diagnose_log_entry(entry)
                if diag:
                    issues.append(diag)
                    # 自動修正を試みる
                    fix = _attempt_fix(diag)
                    if fix:
                        fixes.append(fix)

    # --- 3. ログ書き込みテスト ---
    log_ok = _test_log_write()
    if not log_ok:
        issues.append({
            "check": "ログ書き込み",
            "status": "FAIL",
            "message": "log.jsonl に書き込めません。",
        })
        # マシン負荷チェック
        load_info = _get_system_load()
        if load_info:
            warnings.append({
                "check": "システム負荷",
                "status": "WARN",
                "message": load_info,
            })

    # --- 4. 出力 ---
    print("== se --doctor ==")
    print()

    if not issues and not warnings:
        print("All checks passed. No issues found.")
        return

    if issues:
        print(f"--- Issues ({len(issues)}) ---")
        for i, item in enumerate(issues, 1):
            status = item.get("status", "FAIL")
            msg = item.get("message", item.get("check", "unknown"))
            print(f"  {i}. [{status}] {msg}")
            hint = item.get("hint")
            if hint:
                print(f"     → {hint}")
            fix_r = item.get("_fix_result")
            if fix_r:
                fixes.append(fix_r)
        print()

    if fixes:
        print(f"--- Auto-fixed ({len(fixes)}) ---")
        for f in fixes:
            print(f"  ✓ {f}")
        print()

    if warnings:
        print(f"--- Warnings ({len(warnings)}) ---")
        for w in warnings:
            status = w.get("status", "WARN")
            msg = w.get("message", w.get("check", ""))
            print(f"  ⚠ [{status}] {msg}")

    # doctor結果をログに記録
    if SE_DIR.exists():
        try:
            append_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "doctor",
                "issues": len(issues),
                "fixes": len(fixes),
                "warnings": len(warnings),
                "issue_summary": [i.get("check", "?") for i in issues],
            })
        except Exception:
            pass  # ログに書けなくてもdoctorは続ける


def _check(name: str, fn, error_msg: str | None, target: list, fix_name: str | None = None) -> None:
    """Run a check and append result to target list."""
    try:
        ok = fn()
    except Exception as e:
        ok = False
    if not ok:
        entry = {"check": name, "status": "FAIL"}
        if error_msg:
            entry["message"] = error_msg
        if fix_name and fix_name in KNOWN_ERRORS:
            entry["hint"] = KNOWN_ERRORS[fix_name]["hint"]
            fix_result = _attempt_fix({"_name": fix_name})
            if fix_result:
                entry["_fix_result"] = fix_result
        target.append(entry)


def _everything_running() -> bool:
    """Check if Everything IPC is responding."""
    es = get_es_path()
    try:
        r = subprocess.run([es, "-n", "1", "--", "a"],
                           capture_output=True, text=True, encoding="utf-8",
                           timeout=5)
        # Everything returns 0 even for no results, non-0 if IPC fails
        return r.returncode == 0 or "no results" in r.stdout.lower()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _import_migemo() -> bool:
    try:
        import migemo
        Migemo = migemo.Migemo
        return True
    except ImportError:
        return False


def _test_log_write() -> bool:
    """Test that we can write to the log file."""
    if not SE_DIR.exists():
        return False
    try:
        test_path = SE_DIR / ".write_test"
        test_path.write_text("ok", encoding="utf-8")
        test_path.unlink()
        return True
    except (PermissionError, OSError):
        return False


def _get_system_load() -> str | None:
    """Check system load. Returns warning message if high."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(PROJECT_DIR))
        parts = []
        if cpu > 80:
            parts.append(f"CPU {cpu:.0f}%")
        if mem.percent > 85:
            parts.append(f"RAM {mem.percent:.0f}%")
        if disk.percent > 90:
            parts.append(f"Disk {disk.percent:.0f}%")
        if parts:
            return f"高負荷: {', '.join(parts)}"
        return None
    except ImportError:
        # psutilない→替代: wmic
        try:
            r = subprocess.run(
                ["wmic", "OS", "get", "FreePhysicalMemory", "/value"],
                capture_output=True, text=True, timeout=5)
            if "FreePhysicalMemory" in r.stdout:
                free_kb = int(r.stdout.split("=")[1].strip())
                free_gb = free_kb / 1024 / 1024
                if free_gb < 1:
                    return f"空きメモリ少ない: {free_gb:.1f} GB"
            return None
        except Exception:
            return None


def _scan_log_for_errors(log_path: Path) -> list[dict]:
    """Read log.jsonl and find error entries."""
    errors = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    errors.append({"raw": line, "error": "json_decode"})
                    continue
                if entry.get("error"):
                    errors.append(entry)
    except (PermissionError, OSError):
        pass
    return errors


def _diagnose_log_entry(entry: dict) -> dict | None:
    """Match a log entry against known error patterns."""
    msg = json.dumps(entry, ensure_ascii=False)
    for name, pattern in KNOWN_ERRORS.items():
        if pattern["match"](msg):
            return {
                "check": f"ログ内エラー ({name})",
                "status": "FAIL",
                "message": entry.get("error", msg[:100]),
                "hint": pattern["hint"],
                "_name": name,
            }
    return None


def _attempt_fix(diag: dict) -> str | None:
    """Try to auto-fix an issue. Returns fix description or None."""
    name = diag.get("_name")
    if not name or name not in KNOWN_ERRORS:
        return None
    try:
        result = KNOWN_ERRORS[name]["fix"]()
        return result
    except Exception:
        return None


# --- 個別自動修正関数 ---

def _fix_es_not_found() -> str | None:
    es = get_es_path()
    if not Path(es).exists():
        candidates = [
            r"C:\Program Files\Everything\es.exe",
            r"C:\Program Files (x86)\Everything\es.exe",
            os.path.expanduser(r"~\AppData\Local\Everything\es.exe"),
        ]
        for c in candidates:
            if Path(c).exists():
                return f"es.exe 発見: {c} — ~/.serc の es_path を更新してください"
        return None
    return "es.exe は存在します"


def _fix_everything_not_running() -> str | None:
    es = get_es_path()
    try:
        exe = Path(es).parent / "Everything64.exe"
        if not exe.exists():
            exe = Path(es).parent / "Everything.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], creationflags=0x00000008)  # DETACHED_PROCESS
            import time; time.sleep(2)
            if _everything_running():
                return "Everything を起動しました"
        return None
    except Exception:
        return None


def _fix_migemo() -> str | None:
    try:
        python = sys.executable
        r = subprocess.run(
            [python, "-m", "pip", "install", "pymigemo"],
            capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            return "pymigemo をインストールしました"
    except Exception:
        pass
    return None


def _fix_config_corrupt() -> str | None:
    if CONFIG_PATH.exists():
        bak = CONFIG_PATH.with_suffix(".yaml.corrupt")
        shutil.move(str(CONFIG_PATH), str(bak))
        return f"壊れたconfig → {bak.name} に退避。se --init で再生成してください。"
    return None


def _fix_scope_not_found() -> str | None:
    return "se --init でスコープを再生成してください。"


def _fix_log_write() -> str | None:
    log_path = SE_DIR / "log.jsonl"
    if log_path.exists():
        try:
            os.chmod(str(log_path), 0o644)
            return "log.jsonl の権限を修正しました"
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Search command
# ---------------------------------------------------------------------------

def cmd_search(args) -> None:
    ensure_init()

    raw_query = " ".join(args.query)
    caller = detect_caller()
    allowed_roots = get_allowed_roots(caller)

    # Determine search paths
    search_paths: list[str] | None = None
    if args.scope:
        scope_paths = get_scope_paths(args.scope)
        if scope_paths:
            search_paths = enforce_allowed(scope_paths, allowed_roots)
            if not search_paths:
                print(f"Scope '{args.scope}' outside allowed roots for {caller}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Unknown scope: {args.scope}", file=sys.stderr)
            print("Available: " + ", ".join(list_scopes()), file=sys.stderr)
            sys.exit(1)

    # Check explicit -p path
    if args.path and allowed_roots:
        if not enforce_allowed([args.path], allowed_roots):
            print(f"Path '{args.path}' outside allowed roots for {caller}", file=sys.stderr)
            sys.exit(1)

    # Build regex
    if args.literal:
        regex = raw_query
    else:
        has_jp = any("\u3040" <= c <= "\u9FFF" or "\uFF66" <= c <= "\uFF9F" for c in raw_query)
        if has_jp:
            regex = raw_query
        else:
            try:
                regex = migemo_expand(raw_query)
            except Exception as ex:
                print(f"migemo error: {ex}", file=sys.stderr)
                regex = raw_query

    if args.expand_only:
        print(regex)
        return

    # Search
    if search_paths:
        results = es_search_multi_path(regex, search_paths, args.max)
    else:
        results = es_search(regex, args.path, args.max)

    if allowed_roots:
        results = filter_results(results, allowed_roots)

    if not results:
        print("(no results)", file=sys.stderr)

    # Output
    if results:
        if args.fzf:
            for s in fzf_select(results):
                print(s)
        else:
            for r in results:
                print(r)

    # Log
    if args.log:
        append_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller,
            "session_id": detect_session_id(),
            "cwd": os.getcwd(),
            "query": raw_query,
            "regex": regex if not args.literal else None,
            "scope": args.scope,
            "path": args.path,
            "result_count": len(results),
            "results": results[:50],
        })
        print(f"[logged {len(results)} results]", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="se",
        description="Romaji-aware Everything search (migemo + es)",
    )
    parser.add_argument("query", nargs="*", help="Search query")
    parser.add_argument("--init", action="store_true", help="Initialize .se/ directory")
    parser.add_argument("--doctor", action="store_true", help="Diagnose and fix problems")
    parser.add_argument("-p", "--path", help="Limit search to this path")
    parser.add_argument("-n", "--max", type=int, help="Max results")
    parser.add_argument("-f", "--fzf", action="store_true", help="Fuzzy-filter with fzf")
    parser.add_argument("-e", "--expand-only", action="store_true", help="Show migemo regex only")
    parser.add_argument("--literal", action="store_true", help="No migemo")
    parser.add_argument("--scope", help="Search scope (agents, pi, codex, ...)")
    parser.add_argument("--log", action="store_true", help="Log search to .se/log.jsonl")

    args = parser.parse_args()

    if args.init:
        cmd_init(args)
        return

    if args.doctor:
        cmd_doctor(args)
        return

    if not args.query:
        parser.print_help()
        return

    cmd_search(args)


if __name__ == "__main__":
    main()
