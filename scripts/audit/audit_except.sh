#!/usr/bin/env bash
# Fails if any backend Python file contains bare `except:` or `except Exception: pass`.
set -u

PATTERN_BARE='^[[:space:]]*except[[:space:]]*:'
PATTERN_SWALLOW='except[[:space:]]+[A-Za-z_]*Exception[[:space:]]*:[[:space:]]*$'

PATHS=("backend/app" "backend/tests")

MATCHES=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE "$PATTERN_BARE|$PATTERN_SWALLOW" "$p" --include="*.py" 2>/dev/null
done)

if [ -n "$MATCHES" ]; then
    echo "Found bare or empty exception handlers:"
    echo "$MATCHES"
    exit 1
fi

# Also catch `except ...: pass` followed by only pass
TWO_LINE=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE -A1 '^[[:space:]]*except[[:space:]].*:[[:space:]]*$' "$p" --include="*.py" 2>/dev/null \
        | grep -B1 '^[[:space:]]*pass[[:space:]]*$' \
        | grep -E 'except' || true
done)

if [ -n "$TWO_LINE" ]; then
    echo "Found except ...: pass patterns:"
    echo "$TWO_LINE"
    exit 1
fi

exit 0
