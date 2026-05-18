#!/usr/bin/env python
"""se — romaji-aware Everything search.

Usage:
    se nemusou           # migemo展開 → es -r で検索
    se -p D:\\data term   # パス限定
    se -n 20 query       # 件数制限
    se -f query          # 結果をfzfで絞り込み
    se -e pattern        # migemo展開だけ（検索しない）
    se -- literal word   # esにそのまま渡す（migemoなし）
"""

import argparse
import subprocess
import sys
import shutil

# Python 3.12 at default install location
PYTHON = r"C:\Users\class\AppData\Local\Programs\Python\Python312\python.exe"
ES = r"C:\Program Files\Everything\es.exe"
DEFAULT_PATH = r"D:\data\Pi-Coding-Fun"


def migemo_expand(query: str) -> str:
    """Expand romaji query to Japanese regex via pymigemo."""
    import migemo
    m = migemo.Migemo()
    return m.query(query)


def es_search(regex: str, path: str | None, n: int | None, extra_args: list[str]) -> list[str]:
    """Run es.exe with regex and return results."""
    cmd = [ES, "-r", regex]
    if path:
        cmd += ["-path", path]
    else:
        cmd += ["-path", DEFAULT_PATH]
    if n is not None:
        cmd += ["-n", str(n)]
    cmd += extra_args

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 and result.stderr:
        print(f"es error: {result.stderr.strip()}", file=sys.stderr)
    lines = result.stdout.splitlines()
    return [l for l in lines if l.strip()]


def fzf_select(lines: list[str]) -> list[str]:
    """Pipe results through fzf for interactive selection."""
    fzf = shutil.which("fzf")
    if not fzf:
        print("fzf not found", file=sys.stderr)
        return lines
    result = subprocess.run(
        [fzf, "--layout=reverse", "--preview", "bat --style=header-filename --color=always {} 2>/dev/null || cat {}"],
        input="\n".join(lines),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0:
        return [l for l in result.stdout.splitlines() if l.strip()]
    return []  # cancelled


def main():
    parser = argparse.ArgumentParser(
        prog="se",
        description="Romaji-aware Everything search (migemo + es)",
    )
    parser.add_argument("query", nargs="+", help="Search query (romaji or Japanese)")
    parser.add_argument("-p", "--path", help="Limit search to this path")
    parser.add_argument("-n", "--max", type=int, help="Max results")
    parser.add_argument("-f", "--fzf", action="store_true", help="Fuzzy-filter results with fzf")
    parser.add_argument("-e", "--expand-only", action="store_true", help="Show migemo regex only (don't search)")
    parser.add_argument("--literal", action="store_true", help="Pass query to es as-is (no migemo)")
    args = parser.parse_args()

    raw_query = " ".join(args.query)

    # Literal mode: skip migemo entirely
    if args.literal:
        results = es_search(raw_query, args.path, args.max, [])
        for r in results:
            print(r)
        return

    # Detect if query has Japanese chars → skip migemo, use es directly
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

    results = es_search(regex, args.path, args.max, [])

    if not results:
        print("(no results)", file=sys.stderr)
        return

    if args.fzf:
        selected = fzf_select(results)
        for s in selected:
            print(s)
    else:
        for r in results:
            print(r)


if __name__ == "__main__":
    main()
