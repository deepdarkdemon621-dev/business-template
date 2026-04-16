# L1 Audit Scripts

Mechanical checks that run in CI and pre-push. Each script must exit non-zero on violation and print offending locations.

Invoke all at once:

```bash
bash scripts/audit/run_all.sh
```

## Inventory (Plan 1)

- `audit_except.sh` — no `except: pass` / `except Exception: pass`
- `audit_todo.sh` — new `TODO|FIXME|XXX` require PR ack
- `audit_mock_leak.sh` — `MOCK_` prefix forbidden outside `tests/`
- `audit_json_schema.sh` — no hand-written `*.schema.json` in sources
- `audit_mui_imports.sh` — `@mui/*` and raw `@radix-ui/*` forbidden in pages
- `audit_pagination_fe.sh` — `paginationMode="client"` forbidden
- `audit_permissions.py` — every FastAPI route has `require_perm` or `public=True`
- `audit_listing.py` — list endpoints return `Page[...]` and use `paginate()`

Later plans add more (guards, magic-strings, n+1, etc.).
