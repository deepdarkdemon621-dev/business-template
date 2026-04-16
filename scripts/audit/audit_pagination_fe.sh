#!/usr/bin/env bash
# Fails if `paginationMode="client"` appears in frontend sources.
set -u

MATCHES=$(grep -rn -E 'paginationMode\s*=\s*["'"'"']client["'"'"']' frontend/src 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Client-side pagination is forbidden. All lists must use server pagination."
    echo "$MATCHES"
    exit 1
fi

exit 0
