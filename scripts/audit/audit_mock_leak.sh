#!/usr/bin/env bash
# Fails if MOCK_ identifiers appear outside tests directories.
set -u

BACKEND_MATCHES=$(grep -rnE '\bMOCK_[A-Za-z0-9_]+' backend/app 2>/dev/null || true)
FRONTEND_MATCHES=$(grep -rnE '\bMOCK_[A-Za-z0-9_]+' frontend/src 2>/dev/null \
    | grep -vE '\.test\.(ts|tsx)$' \
    | grep -vE '__tests__/' \
    || true)

if [ -n "$BACKEND_MATCHES" ] || [ -n "$FRONTEND_MATCHES" ]; then
    echo "MOCK_ identifiers leaked into application code:"
    [ -n "$BACKEND_MATCHES" ] && echo "$BACKEND_MATCHES"
    [ -n "$FRONTEND_MATCHES" ] && echo "$FRONTEND_MATCHES"
    echo
    echo "Mock data belongs in backend/tests/ or *.test.ts files only."
    exit 1
fi

exit 0
