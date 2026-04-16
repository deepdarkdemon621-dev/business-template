#!/usr/bin/env bash
# Fails if any hand-authored *.schema.json exists in sources (except generated/).
set -u

MATCHES=$(find backend/app frontend/src -name '*.schema.json' 2>/dev/null \
    | grep -v '/generated/' || true)

if [ -n "$MATCHES" ]; then
    echo "Hand-written JSON Schema files found. Pydantic is the source of truth."
    echo "$MATCHES"
    exit 1
fi

exit 0
