#!/usr/bin/env bash
# Fails if any router.py in modules/ calls .scalars().all() or bare .all() on a Select.
# List endpoints must use paginate().
set -u

PATH_SCAN="backend/app/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

MATCHES=$(grep -rnE '\.scalars\(\)\.all\(\)|\.all\(\)[[:space:]]*$' "$PATH_SCAN" --include='router.py' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found unpaginated .all() calls in router.py — use paginate() instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
