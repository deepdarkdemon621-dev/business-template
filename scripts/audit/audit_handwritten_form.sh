#!/usr/bin/env bash
# Fails if any module page renders form controls directly instead of via <FormRenderer>.
# Field components inside components/form/fields/ are exempt.
set -u

PATH_SCAN="frontend/src/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

PATTERN='<input[[:space:]]|<textarea[[:space:]]|<TextField[[:space:]]|<Input[[:space:]]'

MATCHES=$(grep -rnE "$PATTERN" "$PATH_SCAN" --include='*.tsx' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found hand-rolled form controls in modules/ — use <FormRenderer /> instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
