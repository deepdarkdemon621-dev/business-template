# backend/ — Agent guide

FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic. Python 3.13, uv.

## Layout (read `docs/conventions/08-naming-and-layout.md`)

```
app/
├── core/       shared infra (config, auth, guards, permissions, pagination, errors, audit, storage, workflow)
└── modules/    feature-first; each dir has models.py schemas.py service.py router.py crud.py
```

Create a new feature → copy `modules/_template/` → fill in. Then register its router in `app/api/v1.py`.

## Non-negotiables

### Schemas / validation (01)
- Pydantic only. Field-level via `Field()`; cross-field via `json_schema_extra={"x-rules": [...]}` from the registry.
- Response models set `alias_generator=to_camel` (inherit from shared `BaseSchema` — Plan 2).

### Endpoints (05, 06, 07)
- Every route has `dependencies=[Depends(require_perm("..."))]` OR `public=True`.
- List endpoints inherit `PaginatedEndpoint` (Plan 2); response shape `{items,total,page,size,hasNext}`.
- Errors via `raise ProblemDetails(code=..., status=..., detail=...)` — never bare `HTTPException` without a code.

### Queries (07)
- Protected resources: `apply_scope(select(X), current_user, perm_code, dept_field)`.
- List: `await paginate(session, stmt, page_query)`.
- Never bare `.all()`. Never `.scalars().all()` without pagination in an endpoint.

### Mutations (02)
- Wrap in `async with session.begin():`.
- Run `__guards__` before write (service base handles this).
- Let audit base emit event automatically.

### No-go
- `except:` or `except Exception: pass` — always re-raise or handle with logging.
- Hard-coded secrets, DSN strings, or magic values — use Settings or enums.
- Returning SQLAlchemy objects directly — always via Pydantic response model.

## Commands

```bash
cd backend
uv sync                        # install
uv run pytest                  # tests
uv run ruff check .            # lint
uv run ruff format .           # format
uv run alembic upgrade head    # migrate
uv run alembic revision --autogenerate -m "msg"
```
