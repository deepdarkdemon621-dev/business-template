#!/usr/bin/env bash
# Warns on TODO/FIXME/XXX in source. Fails if count grows without PR ack (ack via `TODO(ack:PR-NNN)`).
set -u

PATHS=("backend/app" "frontend/src")

MATCHES=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE '\b(TODO|FIXME|XXX)\b' "$p" --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null
done)

UNACKED=$(echo "$MATCHES" | grep -vE '\b(TODO|FIXME|XXX)\(ack:' || true)

if [ -n "$UNACKED" ]; then
    echo "Found TODO/FIXME/XXX without PR ack:"
    echo "$UNACKED"
    echo
    echo "Use TODO(ack:PR-123) to acknowledge intentional."
    exit 1
fi

exit 0
