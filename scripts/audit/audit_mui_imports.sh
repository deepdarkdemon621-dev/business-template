#!/usr/bin/env bash
# Fails if @mui is imported anywhere OR @radix-ui is imported outside components/ui.
set -u

MUI=$(grep -rn -E "from ['\"]@mui/" frontend/src 2>/dev/null || true)

RADIX_IN_PAGES=$(grep -rn -E "from ['\"]@radix-ui/" frontend/src 2>/dev/null \
    | grep -vE '^frontend/src/components/ui/' \
    || true)

FAIL=0

if [ -n "$MUI" ]; then
    echo "Found @mui imports (forbidden):"
    echo "$MUI"
    FAIL=1
fi

if [ -n "$RADIX_IN_PAGES" ]; then
    echo "Found @radix-ui imports outside components/ui (forbidden):"
    echo "$RADIX_IN_PAGES"
    FAIL=1
fi

exit $FAIL
