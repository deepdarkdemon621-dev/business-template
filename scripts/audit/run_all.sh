#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

FAIL=0

run() {
    local name="$1"; shift
    echo "── $name ──"
    if "$@"; then
        echo "  PASS"
    else
        echo "  FAIL"
        FAIL=1
    fi
}

run "except"         bash scripts/audit/audit_except.sh
run "todo"           bash scripts/audit/audit_todo.sh
run "mock-leak"      bash scripts/audit/audit_mock_leak.sh
run "json-schema"    bash scripts/audit/audit_json_schema.sh
run "mui-imports"    bash scripts/audit/audit_mui_imports.sh
run "pagination-fe"  bash scripts/audit/audit_pagination_fe.sh

if command -v python >/dev/null 2>&1; then
    run "permissions"   python scripts/audit/audit_permissions.py
    run "listing"       python scripts/audit/audit_listing.py
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "✔ All L1 audits passed."
    exit 0
else
    echo "✘ L1 audits failed."
    exit 1
fi
