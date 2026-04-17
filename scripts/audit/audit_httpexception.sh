#!/usr/bin/env bash
# Fails if any file under backend/app/modules/ raises bare HTTPException.
# Endpoints must raise ProblemDetails instead.
set -u

PATH_SCAN="backend/app/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

MATCHES=$(grep -rnE 'raise[[:space:]]+HTTPException\(' "$PATH_SCAN" --include='*.py' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found bare HTTPException raises — use ProblemDetails instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
