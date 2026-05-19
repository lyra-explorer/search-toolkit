#!/bin/bash
# pre-commit hook: reject personal paths in staged changes
#
# Install:
#   ln -sf ../../scripts/pre-commit-no-personal-paths.sh .git/hooks/pre-commit
#
# Pattern strategy: the username alone matches 2500+ Python lines.
# But "Users/<name>" is a path context — near-zero false positives.

set -euo pipefail

# Only scan staged changes (diff), not entire files
diff=$(git diff --cached --unified=0 --diff-filter=ACMR -- '*.py' '*.md' '*.yaml' '*.yml' '*.txt' '*.json' 2>/dev/null || true)

if [ -z "$diff" ]; then
    exit 0
fi

PATTERNS=(
    # Windows: C:\Users\<USER>\  /c/Users/<user>/  "Users\<user>"
    'Users[/\\]class[/\\"]'
    # Project path (unique enough on its own)
    'Pi-Coding-Fun'
)

found=0
for pat in "${PATTERNS[@]}"; do
    matches=$(echo "$diff" | grep -nP "^[\+].*$pat" 2>/dev/null || true)
    if [ -n "$matches" ]; then
        if [ "$found" -eq 0 ]; then
            echo "" >&2
            echo "❌ Personal path(s) detected in staged changes:" >&2
            echo "" >&2
        fi
        echo "$matches" | sed 's/^/   /' >&2
        found=1
    fi
done

if [ "$found" -eq 1 ]; then
    echo "" >&2
    echo "Replace with <USER> or a generic path before committing." >&2
    echo "" >&2
    exit 1
fi

exit 0
