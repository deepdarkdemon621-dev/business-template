# 05 · API Contract

## Errors: RFC 7807 Problem Details (extended)

All error responses:

```json
{
  "type": "about:blank",
  "title": "Guard violation",
  "status": 409,
  "detail": "Department has 12 users; cannot delete",
  "code": "dept.has-dependents",
  "errors": [],
  "guardViolation": { "guard": "NoDependents", "params": { "table": "users", "count": 12 } }
}
```

| Field | Meaning |
|---|---|
| `type` | URI identifying the problem type (spec uses `about:blank` for common cases) |
| `title` | Short human summary |
| `status` | HTTP status (matches response code) |
| `detail` | Request-specific message |
| `code` | Machine-readable error code (stable across versions) — **use this for FE logic** |
| `errors` | Per-field validation errors `[{field, code, message}]` (for 422) |
| `guard_violation` | Present when a guard triggered; see 02 |

## Pagination

List endpoints:

- **Request:** `?page=1&size=20` (1-based page; `size` capped at 100 server-side)
- **Response shape:**
  ```json
  {
    "items": [...],
    "total": 1234,
    "page": 1,
    "size": 20,
    "hasNext": true
  }
  ```
- Bare arrays are **forbidden** in list responses.
- The `size` param is clamped server-side; client can't exceed 100 even if they request it.

## Response envelope

No outer envelope (no `{code, data, message}` wrapper). Successful responses are the resource itself or the pagination struct above. Errors go through Problem Details. HTTP status codes are authoritative.

## Naming boundary

- Backend (Python / DB / Pydantic internals): `snake_case`
- Wire format (JSON over HTTP): `camelCase`
- Transition: all Pydantic response models set `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` in a shared base class

## List filter / sort / search

- **Filter:** `?status=approved&department_id=3` — query keys match whitelisted fields
- **Sort:** `?sort=-created_at,name` — comma-separated; `-` prefix = descending
- **Search:** `?q=keyword` — backend decides which fields to match
- Unknown filter keys → 400 Problem Details

## Export

For "give me everything" needs, use a dedicated export endpoint:

- `GET /{resource}/export?format=csv` — streams CSV (or xlsx in V2)
- **Not** the list endpoint with `size=huge`

## Versioning

All routes prefixed `/api/v1/...`. Breaking changes → `v2` parallel routes.

## Mechanical enforcement

- `scripts/audit/audit_listing.py` — AST-scans list endpoints; fails if return type is not `Page[X]` (Plan 2 adds `Page` generic)
- `scripts/audit/audit_error_shape.py` (Plan 2) — every `raise HTTPException` must carry a `code`; bare raises fail
- CI: OpenAPI → TS codegen must produce no conflicts with existing `src/api/generated/` before merge

## Concrete endpoint shapes (shipped in Plan 2)

### List endpoints return `Page[T]`

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.pagination import Page, PageQuery, paginate

router = APIRouter()

@router.get("/users", response_model=Page[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    pq: Annotated[PageQuery, Depends()],
) -> Page[UserRead]:
    stmt = select(User).order_by(User.id)
    return await paginate(session, stmt, pq)
```

Wire-format response:

```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "size": 20,
  "hasNext": true
}
```

`size > 100` is silently clamped — never 400.

### Errors always go through Problem Details

```python
from app.core.errors import ProblemDetails, FieldError

raise ProblemDetails(
    code="user.not-found",
    status=404,
    detail="User not found.",
)

raise ProblemDetails(
    code="user.invalid-email",
    status=422,
    detail="Validation failed.",
    errors=[FieldError(field="email", code="format", message="bad email")],
)
```

Content-type is `application/problem+json`. Never raise bare `HTTPException`.

### Frontend HTTP

```ts
import { client } from "@/api/client";
import type { Page } from "@/lib/pagination";

const { data } = await client.get<Page<UserRead>>("/users", { params: { page: 1, size: 20 } });
```

Only `api/client.ts` may call Axios directly. Never `fetch()`, never a second Axios instance.
