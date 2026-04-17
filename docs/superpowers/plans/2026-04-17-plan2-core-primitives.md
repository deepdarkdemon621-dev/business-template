# Plan 2 — Core Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the library-layer primitives every business module will depend on (response base, error model, pagination, service guards, form rules, form renderer, ajv/axios clients), plus three L1 audits — no endpoints, no DB tables, no user-facing features.

**Architecture:** Pure libraries in `backend/app/core/` and `frontend/src/lib/` + `frontend/src/components/form/`. DB-touching helpers (`paginate`, `NoDependents`) take `AsyncSession` as a parameter so they unit-test with mocks. Backend and frontend rule signatures are symmetric (e.g., `mustMatch(a, b)` means the same thing in Pydantic and Ajv). `core/` is a leaf dependency — it must not import from `app/modules/`.

**Tech Stack:** Python 3.13 · FastAPI · Pydantic 2 · SQLAlchemy 2.0 async · pytest-asyncio · uv ; React 19 · Vite 6 · RHF · Ajv 8 · @hookform/resolvers/ajv · shadcn/ui · Vitest · MSW · Axios.

**Spec:** `docs/superpowers/specs/2026-04-17-plan2-core-primitives-design.md` is authoritative. If this plan disagrees with the spec, the spec wins — fix the plan.

---

## File layout

```
backend/app/core/
├── schemas.py        # BaseSchema                                [Task 3]
├── errors.py         # ProblemDetails + FieldError + handler      [Task 4]
├── pagination.py     # PageQuery, Page[T], paginate()             [Task 5]
├── guards.py         # GuardViolationError, NoDependents,         [Task 6]
│                     # StateAllows, ServiceBase
└── form_rules.py     # RuleSpec, date_order, must_match,          [Task 7]
                      # __init_subclass__ hook

backend/tests/core/
├── __init__.py                                                    [Task 2]
├── test_schemas.py                                                [Task 3]
├── test_errors.py                                                 [Task 4]
├── test_pagination.py                                             [Task 5]
├── test_guards.py                                                 [Task 6]
└── test_form_rules.py                                             [Task 7]

backend/tests/
└── test_primitives_integration.py                                 [Task 8]

frontend/src/lib/
├── ajv.ts                                                         [Task 11]
├── form-rules.ts                                                  [Task 11]
├── problem-details.ts                                             [Task 9]
└── pagination.ts                                                  [Task 10]

frontend/src/lib/__tests__/
├── ajv.test.ts                                                    [Task 11]
├── problem-details.test.ts                                        [Task 9]
├── pagination.test.ts                                             [Task 10]
└── primitives.integration.test.tsx                                [Task 19]

frontend/src/api/
└── client.ts                                                      [Task 12]

frontend/src/api/__tests__/
└── client.test.ts                                                 [Task 12]

frontend/src/components/form/
├── FormRenderer.tsx                                               [Task 18]
├── FieldRegistry.ts                                               [Task 13]
├── resolver.ts                                                    [Task 18]
└── fields/
    ├── StringField.tsx                                            [Task 13]
    ├── NumberField.tsx                                            [Task 14]
    ├── BooleanField.tsx                                           [Task 15]
    ├── DateField.tsx                                              [Task 16]
    └── EnumField.tsx                                              [Task 17]

frontend/src/components/form/__tests__/
├── FieldRegistry.test.ts                                          [Task 13]
└── FormRenderer.test.tsx                                          [Task 18]

frontend/src/components/ui/           # via shadcn CLI             [Task 1]
├── input.tsx
├── label.tsx
├── checkbox.tsx
└── select.tsx

scripts/audit/
├── audit_httpexception.sh                                         [Task 20]
├── audit_scalars_all.sh                                           [Task 21]
├── audit_handwritten_form.sh                                      [Task 22]
└── run_all.sh                       # modify                      [Task 23]

docs/conventions/
├── 01-schema-validation.md          # append examples             [Task 24]
├── 02-service-guards.md             # append examples             [Task 25]
├── 04-forms.md                      # append examples             [Task 26]
└── 05-api-contract.md               # append examples             [Task 27]
```

---

## Phase 0 — Setup (2 tasks)

### Task 1: Install missing deps (backend test deps, frontend resolvers + MSW, shadcn primitives)

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/label.tsx`
- Create: `frontend/src/components/ui/checkbox.tsx`
- Create: `frontend/src/components/ui/select.tsx`

- [ ] **Step 1: Add `@hookform/resolvers` and `msw` to frontend**

```bash
cd frontend
npm install @hookform/resolvers
npm install -D msw @testing-library/user-event
```

Verify in `frontend/package.json`:
- `"@hookform/resolvers": "^3.x"` under `dependencies`
- `"msw": "^2.x"` under `devDependencies`
- `"@testing-library/user-event": "^14.x"` under `devDependencies`

- [ ] **Step 2: Add shadcn primitives used by Plan 2 field components**

From `frontend/`, run:

```bash
npx shadcn@latest add input label checkbox select
```

If the CLI prompts for `components.json`, accept defaults (style: `new-york`, base color: `slate`, CSS variables: yes, import alias: `@`). This writes to `frontend/src/components/ui/{input,label,checkbox,select}.tsx` and updates `tailwind.config.js` / `globals.css` if necessary.

If the shadcn CLI fails in this environment, create the four files manually using the canonical shadcn-ui v2 component code (all four are small wrappers around Radix primitives with `cva`-based variants). Do NOT invent your own API — copy shadcn verbatim.

- [ ] **Step 3: Verify frontend build still passes**

```bash
cd frontend && npm run typecheck && npm run lint
```

Expected: both exit 0. Fix any imports the shadcn CLI missed.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/ui/ frontend/components.json frontend/tailwind.config.* frontend/src/index.css
git commit -m "build(plan2): add @hookform/resolvers, msw, shadcn input/label/checkbox/select"
```

---

### Task 2: Create `backend/tests/core/` test package

**Files:**
- Create: `backend/tests/core/__init__.py`

- [ ] **Step 1: Create the empty package file**

```python
# backend/tests/core/__init__.py
```

File is intentionally empty.

- [ ] **Step 2: Verify pytest discovers it**

```bash
cd backend && uv run pytest --collect-only -q
```

Expected: exits 0, existing `test_healthz.py` still collected; no tests in `tests/core/` yet.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/core/__init__.py
git commit -m "test(plan2): scaffold tests/core/ package"
```

---

## Phase A — Backend primitives (5 TDD tasks)

### Task 3: `BaseSchema` (camelCase, populate_by_name, from_attributes, `Z`-suffix datetime)

**Files:**
- Create: `backend/app/core/schemas.py`
- Create: `backend/tests/core/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_schemas.py`:

```python
from datetime import datetime, timezone

import pytest

from app.core.schemas import BaseSchema


class _User(BaseSchema):
    id: int
    display_name: str
    created_at: datetime


def test_serializes_to_camel_case():
    u = _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17, tzinfo=timezone.utc))
    data = u.model_dump(by_alias=True, mode="json")
    assert data == {"id": 1, "displayName": "Ada", "createdAt": "2026-04-17T00:00:00Z"}


def test_accepts_both_camel_and_snake_on_input():
    snake = _User.model_validate({"id": 1, "display_name": "Ada", "created_at": "2026-04-17T00:00:00Z"})
    camel = _User.model_validate({"id": 1, "displayName": "Ada", "createdAt": "2026-04-17T00:00:00Z"})
    assert snake.display_name == "Ada" == camel.display_name


def test_from_attributes_reads_arbitrary_object():
    class _Row:
        id = 1
        display_name = "Ada"
        created_at = datetime(2026, 4, 17, tzinfo=timezone.utc)

    u = _User.model_validate(_Row())
    assert u.display_name == "Ada"


def test_non_utc_datetime_keeps_explicit_offset():
    from datetime import timedelta
    tz = timezone(timedelta(hours=9))
    u = _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17, tzinfo=tz))
    data = u.model_dump(by_alias=True, mode="json")
    # Non-UTC offsets stay as-is (only +00:00 is normalized to Z)
    assert data["createdAt"].endswith("+09:00")


def test_naive_datetime_is_rejected():
    with pytest.raises(Exception):
        _User(id=1, display_name="Ada", created_at=datetime(2026, 4, 17))
```

- [ ] **Step 2: Run to verify all four fail**

```bash
cd backend && uv run pytest tests/core/test_schemas.py -v
```

Expected: every test errors with `ModuleNotFoundError: No module named 'app.core.schemas'`.

- [ ] **Step 3: Implement**

Create `backend/app/core/schemas.py`:

```python
"""Base class for every request and response Pydantic model.

Conventions:
- camelCase at the API boundary (``created_at`` → ``createdAt``).
- Accepts both camelCase and snake_case on input.
- Reads directly from SQLAlchemy instances (``from_attributes=True``).
- Datetimes serialize with an explicit UTC offset; ``+00:00`` is normalized to ``Z``.
- Naive datetimes are rejected at validation time — always attach a tz.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_serializer
from pydantic.alias_generators import to_camel


def _normalize_dt(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        s = value.isoformat()
        return s.replace("+00:00", "Z") if s.endswith("+00:00") else s
    if isinstance(value, dict):
        return {k: _normalize_dt(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_dt(v) for v in value]
    return value


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def _reject_naive_datetime(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return v

    @model_serializer(mode="wrap", when_used="json")
    def _ser_model(self, handler):  # type: ignore[no-untyped-def]
        return _normalize_dt(handler(self))
```

Note on `when_used="json"`: datetime normalization only applies when serializing for the wire (`mode="json"`). Python-mode dumps (`mode="python"`) still yield `datetime` objects.

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/core/test_schemas.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/schemas.py backend/tests/core/test_schemas.py
git commit -m "feat(core): BaseSchema with camelCase + Z-suffix datetime serialization"
```

---

### Task 4: `ProblemDetails` exception + FastAPI handler

**Files:**
- Create: `backend/app/core/errors.py`
- Create: `backend/tests/core/test_errors.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_errors.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import FieldError, GuardViolationCtx, ProblemDetails, install_handlers


def _make_app() -> TestClient:
    app = FastAPI()
    install_handlers(app)

    @app.get("/not-found")
    def _nf():
        raise ProblemDetails(code="user.not-found", status=404, detail="User not found.")

    @app.get("/validation")
    def _v():
        raise ProblemDetails(
            code="user.invalid-email",
            status=422,
            detail="Validation failed.",
            errors=[FieldError(field="email", code="format", message="bad email")],
        )

    @app.get("/guard")
    def _g():
        raise ProblemDetails(
            code="department.has-users",
            status=409,
            detail="cannot delete",
            guard_violation=GuardViolationCtx(guard="NoDependents", params={"relation": "users"}),
        )

    return TestClient(app)


def test_problem_details_serialization_basic():
    r = _make_app().get("/not-found")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body == {
        "type": "about:blank",
        "title": "Not Found",
        "status": 404,
        "detail": "User not found.",
        "code": "user.not-found",
    }


def test_problem_details_with_field_errors():
    body = _make_app().get("/validation").json()
    assert body["code"] == "user.invalid-email"
    assert body["errors"] == [{"field": "email", "code": "format", "message": "bad email"}]


def test_problem_details_with_guard_violation():
    body = _make_app().get("/guard").json()
    assert body["guardViolation"] == {"guard": "NoDependents", "params": {"relation": "users"}}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/core/test_errors.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.errors'`.

- [ ] **Step 3: Implement**

Create `backend/app/core/errors.py`:

```python
"""RFC 7807 Problem Details.

Endpoints MUST raise ``ProblemDetails`` — never bare ``HTTPException``.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.schemas import BaseSchema


class FieldError(BaseSchema):
    field: str
    code: str
    message: str | None = None


class GuardViolationCtx(BaseSchema):
    guard: str
    params: dict[str, Any] = {}


class ProblemDetails(Exception):
    def __init__(
        self,
        *,
        code: str,
        status: int,
        detail: str,
        title: str | None = None,
        type: str = "about:blank",
        errors: list[FieldError] | None = None,
        guard_violation: GuardViolationCtx | None = None,
    ) -> None:
        self.code = code
        self.status = status
        self.detail = detail
        self.title = title or HTTPStatus(status).phrase
        self.type = type
        self.errors = errors
        self.guard_violation = guard_violation
        super().__init__(detail)

    def to_body(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "code": self.code,
        }
        if self.errors is not None:
            body["errors"] = [e.model_dump(by_alias=True, mode="json") for e in self.errors]
        if self.guard_violation is not None:
            body["guardViolation"] = self.guard_violation.model_dump(by_alias=True, mode="json")
        return body


def install_handlers(app: FastAPI) -> None:
    """Register the ProblemDetails handler on a FastAPI app."""

    @app.exception_handler(ProblemDetails)
    async def _pd_handler(_req: Request, exc: ProblemDetails) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content=exc.to_body(),
            media_type="application/problem+json",
        )
```

- [ ] **Step 4: Wire into main app**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import install_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="business-template",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
    )

    install_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["infra"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/core/test_errors.py tests/test_healthz.py -v
```

Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/errors.py backend/app/main.py backend/tests/core/test_errors.py
git commit -m "feat(core): ProblemDetails exception and FastAPI handler"
```

---

### Task 5: `PageQuery`, `Page[T]`, `paginate()`

**Files:**
- Create: `backend/app/core/pagination.py`
- Create: `backend/tests/core/test_pagination.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_pagination.py`:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.core.pagination import PageQuery, paginate


def _mock_session(total: int, rows: list):
    session = AsyncMock()
    # COUNT(*) returns `total`; the second execute returns rows as `.scalars().all()`.
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    row_result = MagicMock()
    row_result.scalars.return_value.all.return_value = rows
    session.execute.side_effect = [count_result, row_result]
    return session


class _T:
    """Placeholder table-like class used only as a type marker in the Select."""


@pytest.fixture
def stmt():
    # any Select is fine — paginate does not inspect its contents
    return select(1)


async def test_page_one_has_next(stmt):
    session = _mock_session(total=42, rows=[{"id": i} for i in range(20)])
    page = await paginate(session, stmt, PageQuery(page=1, size=20))
    assert page.total == 42
    assert page.page == 1
    assert page.size == 20
    assert page.has_next is True
    assert len(page.items) == 20


async def test_last_page_has_next_false(stmt):
    session = _mock_session(total=42, rows=[{"id": i} for i in range(2)])
    page = await paginate(session, stmt, PageQuery(page=3, size=20))
    assert page.has_next is False
    assert len(page.items) == 2


async def test_size_above_cap_is_clamped_to_100(stmt):
    # Pydantic validation happens on PageQuery construction; a size>100 via query-string
    # should surface via PageQuery(size=101) and be clamped silently.
    pq = PageQuery.model_validate({"page": 1, "size": 500})
    assert pq.size == 100


async def test_size_below_one_is_clamped_to_one(stmt):
    pq = PageQuery.model_validate({"page": 1, "size": 0})
    assert pq.size == 1


async def test_page_below_one_is_clamped_to_one(stmt):
    pq = PageQuery.model_validate({"page": -2, "size": 20})
    assert pq.page == 1
```

- [ ] **Step 2: Run to verify fail**

```bash
cd backend && uv run pytest tests/core/test_pagination.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `backend/app/core/pagination.py`:

```python
"""Server-side pagination primitives.

List endpoints MUST return ``Page[T]`` and MUST use ``paginate()``. Never return
``list[T]`` and never call ``.scalars().all()`` on a Select in an endpoint.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.schemas import BaseSchema

T = TypeVar("T")

MAX_PAGE_SIZE = 100


class PageQuery(BaseModel):
    """FastAPI query-param dependency.

    Use ``Depends(PageQuery)`` or inherit ``PaginatedEndpoint`` (Plan 3+).
    Values outside limits are silently clamped, never rejected.
    """

    page: int = Field(default=1)
    size: int = Field(default=20)
    sort: str | None = None
    q: str | None = None

    @field_validator("page", mode="before")
    @classmethod
    def _clamp_page(cls, v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 1
        return max(1, n)

    @field_validator("size", mode="before")
    @classmethod
    def _clamp_size(cls, v: Any) -> int:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return 20
        return max(1, min(MAX_PAGE_SIZE, n))


class Page(BaseSchema, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    has_next: bool


async def paginate(
    session: AsyncSession,
    stmt: Select,
    pq: PageQuery,
) -> Page[Any]:
    """Execute COUNT(*) over stmt, then LIMIT/OFFSET stmt. Returns a Page.

    The caller is responsible for applying filter/sort/search to ``stmt`` before
    passing it in. ``paginate`` only handles counting and slicing.
    """
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    offset = (pq.page - 1) * pq.size
    rows_stmt = stmt.offset(offset).limit(pq.size)
    rows_result = await session.execute(rows_stmt)
    items = list(rows_result.scalars().all())

    has_next = (pq.page * pq.size) < total
    return Page(items=items, total=total, page=pq.page, size=pq.size, has_next=has_next)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/core/test_pagination.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/pagination.py backend/tests/core/test_pagination.py
git commit -m "feat(core): PageQuery, Page[T], paginate() with silent clamping"
```

---

### Task 6: Service guards — `GuardViolationError`, `NoDependents`, `StateAllows`, `ServiceBase`

**Files:**
- Create: `backend/app/core/guards.py`
- Create: `backend/tests/core/test_guards.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_guards.py`:

```python
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.guards import (
    GuardViolationError,
    NoDependents,
    ServiceBase,
    StateAllows,
)


@pytest.fixture
def session():
    return AsyncMock()


async def test_no_dependents_passes_when_count_zero(session):
    result = MagicMock()
    result.scalar_one.return_value = 0
    session.execute.return_value = result

    guard = NoDependents(relation="users", fk_col="department_id")
    await guard.check(session, SimpleNamespace(id=1))


async def test_no_dependents_raises_when_count_positive(session):
    result = MagicMock()
    result.scalar_one.return_value = 3
    session.execute.return_value = result

    guard = NoDependents(relation="users", fk_col="department_id")
    with pytest.raises(GuardViolationError) as ei:
        await guard.check(session, SimpleNamespace(id=1))
    assert ei.value.code == "has-dependents"
    assert ei.value.ctx == {"relation": "users", "fk_col": "department_id", "count": 3}


async def test_state_allows_passes(session):
    guard = StateAllows(field="status", allowed=["draft", "open"])
    await guard.check(session, SimpleNamespace(status="draft"))


async def test_state_allows_raises_with_ctx(session):
    guard = StateAllows(field="status", allowed=["draft", "open"])
    with pytest.raises(GuardViolationError) as ei:
        await guard.check(session, SimpleNamespace(status="closed"))
    assert ei.value.code == "state-not-allowed"
    assert ei.value.ctx == {"field": "status", "actual": "closed", "allowed": ["draft", "open"]}


async def test_service_base_runs_delete_guards(session):
    calls: list[str] = []

    class _Guard:
        async def check(self, s, i):
            calls.append("checked")

    class _Model:
        __tablename__ = "t"
        __guards__ = {"delete": [_Guard(), _Guard()]}

    svc = ServiceBase()
    svc.model = _Model
    instance = SimpleNamespace(id=7)

    await svc.delete(session, instance)

    assert calls == ["checked", "checked"]
    session.delete.assert_awaited_once_with(instance)


async def test_service_base_aborts_on_guard_failure(session):
    class _Guard:
        async def check(self, s, i):
            raise GuardViolationError(code="has-dependents", ctx={"relation": "x"})

    class _Model:
        __tablename__ = "t"
        __guards__ = {"delete": [_Guard()]}

    svc = ServiceBase()
    svc.model = _Model

    with pytest.raises(GuardViolationError):
        await svc.delete(session, SimpleNamespace(id=1))
    session.delete.assert_not_called()
```

- [ ] **Step 2: Run tests to verify fail**

```bash
cd backend && uv run pytest tests/core/test_guards.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

Create `backend/app/core/guards.py`:

```python
"""Service-layer invariants.

Guards are declarative: attach them to a model via ``__guards__`` and ``ServiceBase``
runs them before the corresponding mutation. DB-level ON DELETE RESTRICT remains
the belt; guards are the braces — both are required.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession


class GuardViolationError(Exception):
    def __init__(self, *, code: str, ctx: dict[str, Any]) -> None:
        self.code = code
        self.ctx = ctx
        super().__init__(code)


@runtime_checkable
class Guard(Protocol):
    async def check(self, session: AsyncSession, instance: Any) -> None: ...


class NoDependents:
    """Fails if any row in ``relation`` references ``instance.id`` via ``fk_col``.

    ``relation`` is the SQL table name of the dependent (e.g., ``"users"``).
    ``fk_col`` is the FK column on that table (e.g., ``"department_id"``).
    """

    def __init__(self, relation: str, fk_col: str) -> None:
        self.relation = relation
        self.fk_col = fk_col

    async def check(self, session: AsyncSession, instance: Any) -> None:
        stmt = select(func.count()).select_from(
            text(self.relation)
        ).where(text(f"{self.fk_col} = :pk")).params(pk=instance.id)
        count = (await session.execute(stmt)).scalar_one()
        if count > 0:
            raise GuardViolationError(
                code="has-dependents",
                ctx={"relation": self.relation, "fk_col": self.fk_col, "count": int(count)},
            )


class StateAllows:
    """Fails unless ``getattr(instance, field)`` is in ``allowed``."""

    def __init__(self, field: str, allowed: list[Any]) -> None:
        self.field = field
        self.allowed = list(allowed)

    async def check(self, session: AsyncSession, instance: Any) -> None:
        actual = getattr(instance, self.field)
        if actual not in self.allowed:
            raise GuardViolationError(
                code="state-not-allowed",
                ctx={"field": self.field, "actual": actual, "allowed": list(self.allowed)},
            )


class ServiceBase:
    """Base class for module services. Auto-runs ``model.__guards__`` before mutations.

    Subclasses set ``model = <SqlAlchemyModel>``. Plan 3+ will extend with ``update()``.
    """

    model: type

    async def delete(self, session: AsyncSession, instance: Any) -> None:
        guards = getattr(self.model, "__guards__", {}).get("delete", [])
        for guard in guards:
            await guard.check(session, instance)
        await session.delete(instance)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && uv run pytest tests/core/test_guards.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/guards.py backend/tests/core/test_guards.py
git commit -m "feat(core): service guards — NoDependents, StateAllows, ServiceBase"
```

---

### Task 7: Form rules — `RuleSpec`, `date_order`, `must_match`, `__init_subclass__` hook

**Files:**
- Create: `backend/app/core/form_rules.py`
- Create: `backend/tests/core/test_form_rules.py`
- Modify: `backend/app/core/schemas.py` (add `__init_subclass__` hook)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/core/test_form_rules.py`:

```python
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.form_rules import FormRuleRegistry, date_order, must_match
from app.core.schemas import BaseSchema


class _PasswordReset(BaseSchema):
    new_password: str
    confirm: str
    __rules__ = [must_match(a="new_password", b="confirm")]


class _DateRange(BaseSchema):
    starts_on: date
    ends_on: date
    __rules__ = [date_order(start="starts_on", end="ends_on")]


def test_must_match_fires_on_mismatch():
    with pytest.raises(ValidationError) as ei:
        _PasswordReset(new_password="a", confirm="b")
    assert any(e["type"] == "value_error" for e in ei.value.errors())


def test_must_match_passes_on_match():
    m = _PasswordReset(new_password="a", confirm="a")
    assert m.new_password == "a"


def test_date_order_fires_when_end_before_start():
    with pytest.raises(ValidationError):
        _DateRange(starts_on=date(2026, 4, 17), ends_on=date(2026, 4, 1))


def test_date_order_passes_when_end_after_start():
    _DateRange(starts_on=date(2026, 4, 1), ends_on=date(2026, 4, 17))


def test_x_rules_appears_in_json_schema_with_camel_case_field_names():
    schema = _PasswordReset.model_json_schema(by_alias=True)
    assert "x-rules" in schema
    rules = schema["x-rules"]
    assert rules == [{"name": "mustMatch", "params": {"a": "newPassword", "b": "confirm"}}]


def test_date_order_x_rules_in_schema():
    schema = _DateRange.model_json_schema(by_alias=True)
    assert schema["x-rules"] == [
        {"name": "dateOrder", "params": {"start": "startsOn", "end": "endsOn"}}
    ]


def test_registry_rejects_unknown_rule_name():
    assert "mustMatch" in FormRuleRegistry._rules
    assert "dateOrder" in FormRuleRegistry._rules


def test_schema_without_rules_has_no_x_rules_key():
    class _Plain(BaseSchema):
        name: str

    assert "x-rules" not in _Plain.model_json_schema()
```

- [ ] **Step 2: Run to verify fail**

```bash
cd backend && uv run pytest tests/core/test_form_rules.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `form_rules.py`**

Create `backend/app/core/form_rules.py`:

```python
"""Cross-field validation vocabulary.

Rule signatures are symmetric with the frontend Ajv keywords. Adding a new rule
requires implementing BOTH sides (Python factory + Ajv keyword) in the same PR.

Usage on a schema::

    class PasswordReset(BaseSchema):
        new_password: str
        confirm: str
        __rules__ = [must_match(a="new_password", b="confirm")]

The ``BaseSchema.__init_subclass__`` hook walks ``__rules__`` and does two things:
1. Emits ``x-rules`` into ``model_json_schema()`` for frontend Ajv to consume.
2. Registers a ``@model_validator(mode='after')`` that runs the same check server-side.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable

from pydantic.alias_generators import to_camel


@dataclass
class RuleSpec:
    """One entry in a schema's ``__rules__`` list."""

    name: str  # camelCase keyword name, e.g. "mustMatch"
    params: dict[str, Any]  # snake_case field names; rendered as camelCase in x-rules
    validate: Callable[[Any], None]
    """Called with the model instance; must raise ValueError on violation."""


class FormRuleRegistry:
    """Single source of truth for rule names. Plan 2 ships dateOrder and mustMatch."""

    _rules: dict[str, Callable[..., RuleSpec]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[..., RuleSpec]) -> None:
        if name in cls._rules:
            raise ValueError(f"rule {name!r} already registered")
        cls._rules[name] = factory

    @classmethod
    def is_registered(cls, name: str) -> bool:
        return name in cls._rules


def _camel_params(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in params.items():
        # camel-case *values* only when they look like field references
        if isinstance(v, str) and v.isidentifier():
            out[k] = to_camel(v)
        else:
            out[k] = v
    return out


def must_match(*, a: str, b: str) -> RuleSpec:
    def _check(instance: Any) -> None:
        va = getattr(instance, a)
        vb = getattr(instance, b)
        if va != vb:
            raise ValueError(f"{a} must equal {b}")

    return RuleSpec(
        name="mustMatch",
        params={"a": to_camel(a), "b": to_camel(b)},
        validate=_check,
    )


def date_order(*, start: str, end: str) -> RuleSpec:
    def _check(instance: Any) -> None:
        s = getattr(instance, start, None)
        e = getattr(instance, end, None)
        if s is None or e is None:
            return
        if not isinstance(s, (date, datetime)) or not isinstance(e, (date, datetime)):
            raise ValueError(f"{start} and {end} must be dates")
        if e <= s:
            raise ValueError(f"{end} must be after {start}")

    return RuleSpec(
        name="dateOrder",
        params={"start": to_camel(start), "end": to_camel(end)},
        validate=_check,
    )


FormRuleRegistry.register("mustMatch", must_match)
FormRuleRegistry.register("dateOrder", date_order)
```

- [ ] **Step 4: Extend `BaseSchema` with the `__init_subclass__` hook**

Modify `backend/app/core/schemas.py` — append to the existing class:

```python
# Add to imports at top:
from pydantic import model_validator

# Inside class BaseSchema, after model_config and the existing validators:

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        rules = cls.__dict__.get("__rules__")
        if not rules:
            return

        # 1. Inject x-rules into JSON Schema output
        extra = dict(getattr(cls.model_config, "json_schema_extra", None) or {})
        extra["x-rules"] = [{"name": r.name, "params": r.params} for r in rules]
        cls.model_config = {**cls.model_config, "json_schema_extra": extra}  # type: ignore[misc]
        cls.model_rebuild(force=True)

        # 2. Attach a model validator that runs each rule's check on instances
        @model_validator(mode="after")
        def _apply_rules(self: "BaseSchema") -> "BaseSchema":
            for rule in rules:
                rule.validate(self)
            return self

        setattr(cls, "_apply_rules", classmethod(_apply_rules))  # type: ignore[arg-type]
        cls.__pydantic_decorators__.model_validators["_apply_rules"] = (
            _apply_rules.decorator_info  # type: ignore[attr-defined]
        )
        cls.model_rebuild(force=True)
```

If the `__pydantic_decorators__` manipulation proves brittle, fall back to requiring subclasses to `import form_rules` and decorate manually — but only if the direct approach cannot be made to work. First, try wiring the validator by constructing the subclass via a small metaclass helper:

```python
# Alternative: use a helper that builds the validator before Pydantic sees the class.
# If __init_subclass__ cannot cleanly re-register model_validators in Pydantic 2.9+,
# switch to the factory-function pattern:
#
#     def _attach_rules(cls):
#         @model_validator(mode="after")
#         def _run(self):
#             for r in cls.__rules__: r.validate(self)
#             return self
#         cls._apply_rules = _run
#         return cls
#
# and call it via @_attach_rules decorator in user code. Document whichever lands.
```

Pick the approach that passes the tests on the installed Pydantic version. Document the chosen path in a one-line comment above `__init_subclass__`.

- [ ] **Step 5: Run tests**

```bash
cd backend && uv run pytest tests/core/test_form_rules.py tests/core/test_schemas.py -v
```

Expected: all tests in both files pass (9 in form_rules + 5 in schemas = 14).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/form_rules.py backend/app/core/schemas.py backend/tests/core/test_form_rules.py
git commit -m "feat(core): FormRuleRegistry — must_match, date_order, x-rules emission"
```

---

## Phase B — Backend integration (1 task)

### Task 8: End-to-end wiring test

**Files:**
- Create: `backend/tests/test_primitives_integration.py`

- [ ] **Step 1: Write integration test**

Create `backend/tests/test_primitives_integration.py`:

```python
"""Smoke test: wire a fake 'items' resource that uses every Plan 2 primitive
and assert the composed behavior. Intentionally throwaway — Plan 3's first
real endpoint supersedes it.
"""
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import ProblemDetails, install_handlers
from app.core.guards import GuardViolationError, NoDependents, ServiceBase
from app.core.pagination import Page, PageQuery, paginate
from app.core.schemas import BaseSchema


class ItemRead(BaseSchema):
    id: int
    display_name: str


class _FakeItem:
    id: int
    display_name: str
    __tablename__ = "items"
    __guards__ = {"delete": [NoDependents(relation="sub_items", fk_col="item_id")]}

    def __init__(self, id: int, name: str):
        self.id = id
        self.display_name = name


class _ItemService(ServiceBase):
    model = _FakeItem


def _make_app_and_session():
    app = FastAPI()
    install_handlers(app)

    session = AsyncMock()

    async def get_session():
        return session

    @app.get("/items", response_model=Page[ItemRead])
    async def list_items(
        session: Annotated[AsyncMock, Depends(get_session)],
        pq: Annotated[PageQuery, Depends()],
    ):
        stmt = select(_FakeItem)
        return await paginate(session, stmt, pq)

    @app.delete("/items/{item_id}", status_code=204)
    async def delete_item(
        item_id: int,
        session: Annotated[AsyncMock, Depends(get_session)],
    ):
        instance = _FakeItem(id=item_id, name="dummy")
        try:
            await _ItemService().delete(session, instance)
        except GuardViolationError as e:
            raise ProblemDetails(
                code="item.has-dependents",
                status=409,
                detail="Cannot delete item with dependents.",
                guard_violation=__import__("app.core.errors", fromlist=["GuardViolationCtx"])
                .GuardViolationCtx(guard="NoDependents", params=e.ctx),
            )
        return None

    return TestClient(app), session


def _prime_list(session, total: int, items: list[_FakeItem]):
    count_result = MagicMock()
    count_result.scalar_one.return_value = total
    row_result = MagicMock()
    row_result.scalars.return_value.all.return_value = items
    session.execute.side_effect = [count_result, row_result]


def test_list_endpoint_returns_page_shape():
    client, session = _make_app_and_session()
    _prime_list(session, total=3, items=[_FakeItem(i, f"item-{i}") for i in range(1, 4)])

    r = client.get("/items?page=1&size=5")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "items": [
            {"id": 1, "displayName": "item-1"},
            {"id": 2, "displayName": "item-2"},
            {"id": 3, "displayName": "item-3"},
        ],
        "total": 3,
        "page": 1,
        "size": 5,
        "hasNext": False,
    }


def test_size_clamped_silently():
    client, session = _make_app_and_session()
    _prime_list(session, total=0, items=[])
    r = client.get("/items?size=500")
    assert r.status_code == 200
    assert r.json()["size"] == 100


def test_delete_triggers_guard_and_returns_problem_details():
    client, session = _make_app_and_session()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 7  # dependents exist
    session.execute.return_value = count_result

    r = client.delete("/items/1")
    assert r.status_code == 409
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["code"] == "item.has-dependents"
    assert body["guardViolation"]["guard"] == "NoDependents"
    assert body["guardViolation"]["params"]["count"] == 7
```

- [ ] **Step 2: Run**

```bash
cd backend && uv run pytest tests/test_primitives_integration.py -v
```

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_primitives_integration.py
git commit -m "test(core): end-to-end wiring — pagination + guards + problem details"
```

---

## Phase C — Frontend libs (4 tasks)

### Task 9: `problem-details.ts` — typed parser

**Files:**
- Create: `frontend/src/lib/problem-details.ts`
- Create: `frontend/src/lib/__tests__/problem-details.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/lib/__tests__/problem-details.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { isProblemDetails, type ProblemDetails } from "../problem-details";

describe("isProblemDetails", () => {
  it("returns true for a minimal valid body", () => {
    const body: ProblemDetails = {
      type: "about:blank",
      title: "Not Found",
      status: 404,
      detail: "x",
      code: "user.not-found",
    };
    expect(isProblemDetails(body)).toBe(true);
  });

  it("accepts optional errors and guardViolation", () => {
    const body = {
      type: "about:blank",
      status: 409,
      detail: "x",
      code: "u.x",
      errors: [{ field: "email", code: "format" }],
      guardViolation: { guard: "NoDependents", params: { relation: "users" } },
    };
    expect(isProblemDetails(body)).toBe(true);
  });

  it("returns false for unrelated shapes", () => {
    expect(isProblemDetails({ message: "oops" })).toBe(false);
    expect(isProblemDetails(null)).toBe(false);
    expect(isProblemDetails("oops")).toBe(false);
    expect(isProblemDetails({ status: 500, detail: "x" })).toBe(false); // missing code
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/lib/__tests__/problem-details.test.ts
```

Expected: fail — module missing.

- [ ] **Step 3: Implement**

Create `frontend/src/lib/problem-details.ts`:

```ts
export interface FieldError {
  field: string;
  code: string;
  message?: string;
}

export interface GuardViolationCtx {
  guard: string;
  params: Record<string, unknown>;
}

export interface ProblemDetails {
  type: string;
  title?: string;
  status: number;
  detail: string;
  code: string;
  errors?: FieldError[];
  guardViolation?: GuardViolationCtx;
}

export function isProblemDetails(x: unknown): x is ProblemDetails {
  if (x === null || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o.type === "string" &&
    typeof o.status === "number" &&
    typeof o.detail === "string" &&
    typeof o.code === "string"
  );
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/lib/__tests__/problem-details.test.ts
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/problem-details.ts frontend/src/lib/__tests__/problem-details.test.ts
git commit -m "feat(lib): Problem Details types and type guard"
```

---

### Task 10: `pagination.ts` — types

**Files:**
- Create: `frontend/src/lib/pagination.ts`
- Create: `frontend/src/lib/__tests__/pagination.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/lib/__tests__/pagination.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { Page, PageQuery } from "../pagination";

describe("pagination types", () => {
  it("Page<T> accepts items and metadata", () => {
    const p: Page<{ id: number }> = {
      items: [{ id: 1 }],
      total: 1,
      page: 1,
      size: 20,
      hasNext: false,
    };
    expect(p.items.length).toBe(1);
  });

  it("PageQuery fields are all optional", () => {
    const q: PageQuery = {};
    expect(q).toEqual({});
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/lib/__tests__/pagination.test.ts
```

Expected: fail — module missing.

- [ ] **Step 3: Implement**

Create `frontend/src/lib/pagination.ts`:

```ts
export interface PageQuery {
  page?: number;
  size?: number;
  sort?: string;
  q?: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  hasNext: boolean;
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/lib/__tests__/pagination.test.ts
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/pagination.ts frontend/src/lib/__tests__/pagination.test.ts
git commit -m "feat(lib): Page<T> and PageQuery types"
```

---

### Task 11: `ajv.ts` singleton + `form-rules.ts` keyword registration

**Files:**
- Create: `frontend/src/lib/ajv.ts`
- Create: `frontend/src/lib/form-rules.ts`
- Create: `frontend/src/lib/__tests__/ajv.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/lib/__tests__/ajv.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { ajv } from "../ajv";

describe("ajv singleton", () => {
  it("exposes a single instance across imports", async () => {
    const again = (await import("../ajv")).ajv;
    expect(ajv).toBe(again);
  });

  it("mustMatch passes when fields match", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { a: { type: "string" }, b: { type: "string" } },
      mustMatch: { a: "a", b: "b" },
    });
    expect(validate({ a: "x", b: "x" })).toBe(true);
    expect(validate({ a: "x", b: "y" })).toBe(false);
  });

  it("dateOrder passes when end > start", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { startsOn: { type: "string" }, endsOn: { type: "string" } },
      dateOrder: { start: "startsOn", end: "endsOn" },
    });
    expect(validate({ startsOn: "2026-04-01", endsOn: "2026-04-17" })).toBe(true);
    expect(validate({ startsOn: "2026-04-17", endsOn: "2026-04-01" })).toBe(false);
  });

  it("dateOrder skips when either side missing", () => {
    const validate = ajv.compile({
      type: "object",
      properties: { startsOn: { type: "string" }, endsOn: { type: "string" } },
      dateOrder: { start: "startsOn", end: "endsOn" },
    });
    expect(validate({})).toBe(true);
    expect(validate({ startsOn: "2026-04-01" })).toBe(true);
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/lib/__tests__/ajv.test.ts
```

Expected: fail — module missing.

- [ ] **Step 3: Implement `form-rules.ts`**

Create `frontend/src/lib/form-rules.ts`:

```ts
import type Ajv from "ajv";

interface MustMatchParams {
  a: string;
  b: string;
}

interface DateOrderParams {
  start: string;
  end: string;
}

export function registerRuleKeywords(ajv: Ajv): void {
  ajv.addKeyword({
    keyword: "mustMatch",
    type: "object",
    errors: true,
    validate: function mustMatch(params: MustMatchParams, data: Record<string, unknown>) {
      const ok = data[params.a] === data[params.b];
      if (!ok) {
        // @ts-expect-error — Ajv attaches errors on the function
        mustMatch.errors = [
          { keyword: "mustMatch", message: `${params.a} must equal ${params.b}`, params },
        ];
      }
      return ok;
    },
  });

  ajv.addKeyword({
    keyword: "dateOrder",
    type: "object",
    errors: true,
    validate: function dateOrder(params: DateOrderParams, data: Record<string, unknown>) {
      const s = data[params.start];
      const e = data[params.end];
      if (s == null || e == null) return true;
      if (typeof s !== "string" || typeof e !== "string") return false;
      const ok = new Date(e) > new Date(s);
      if (!ok) {
        // @ts-expect-error
        dateOrder.errors = [
          { keyword: "dateOrder", message: `${params.end} must be after ${params.start}`, params },
        ];
      }
      return ok;
    },
  });
}
```

- [ ] **Step 4: Implement `ajv.ts`**

Create `frontend/src/lib/ajv.ts`:

```ts
import Ajv from "ajv";
import addFormats from "ajv-formats";
import { registerRuleKeywords } from "./form-rules";

export const ajv = new Ajv({
  allErrors: true,
  strictSchema: false,
  useDefaults: true,
});

addFormats(ajv);
registerRuleKeywords(ajv);
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx vitest run src/lib/__tests__/ajv.test.ts
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/ajv.ts frontend/src/lib/form-rules.ts frontend/src/lib/__tests__/ajv.test.ts
git commit -m "feat(lib): ajv singleton with mustMatch and dateOrder keywords"
```

---

### Task 12: `api/client.ts` — Axios + Problem Details interceptor

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/__tests__/client.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/api/__tests__/client.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";
import { client } from "../client";
import { isProblemDetails } from "@/lib/problem-details";

describe("api client", () => {
  it("rejects with a ProblemDetails payload when server returns application/problem+json", async () => {
    const pd = {
      type: "about:blank",
      title: "Conflict",
      status: 409,
      detail: "nope",
      code: "dep.has-users",
    };

    // Intercept via the adapter
    client.defaults.adapter = async () => {
      const err: unknown = {
        isAxiosError: true,
        response: {
          status: 409,
          headers: { "content-type": "application/problem+json" },
          data: pd,
        },
      };
      throw err;
    };

    await expect(client.get("/x")).rejects.toSatisfy(isProblemDetails);
  });

  it("rejects with the raw error for non-Problem responses", async () => {
    client.defaults.adapter = async () => {
      throw { isAxiosError: true, response: { status: 500, data: "boom" } };
    };

    await expect(client.get("/x")).rejects.toMatchObject({ response: { status: 500 } });
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/api/__tests__/client.test.ts
```

Expected: fail — module missing.

- [ ] **Step 3: Implement**

Create `frontend/src/api/client.ts`:

```ts
import axios, { AxiosError } from "axios";
import { isProblemDetails } from "@/lib/problem-details";

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  headers: { "Content-Type": "application/json" },
});

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    const data = err.response?.data;
    if (isProblemDetails(data)) {
      // Plan 3 extends this to auto-refresh on 401; Plan 2 ships the stub.
      return Promise.reject(data);
    }
    return Promise.reject(err);
  },
);
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/api/__tests__/client.test.ts
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts
git commit -m "feat(api): Axios client with Problem Details interceptor"
```

---

## Phase D — Frontend form (6 tasks)

### Task 13: `FieldRegistry.ts` + `StringField`

**Files:**
- Create: `frontend/src/components/form/FieldRegistry.ts`
- Create: `frontend/src/components/form/fields/StringField.tsx`
- Create: `frontend/src/components/form/__tests__/FieldRegistry.test.ts`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/form/__tests__/FieldRegistry.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { resolveFieldComponent } from "../FieldRegistry";

describe("FieldRegistry.resolveFieldComponent", () => {
  it("returns StringField for {type: 'string'}", () => {
    const Comp = resolveFieldComponent({ type: "string" });
    expect(Comp.displayName || Comp.name).toBe("StringField");
  });

  it("respects x-widget override", () => {
    const Comp = resolveFieldComponent({ type: "string", "x-widget": "date" });
    expect(Comp.displayName || Comp.name).toBe("DateField");
  });

  it("throws for unsupported type", () => {
    expect(() => resolveFieldComponent({ type: "whatever" })).toThrow();
  });
});
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/FieldRegistry.test.ts
```

Expected: fail — modules missing.

- [ ] **Step 3: Create placeholder Field components**

Create five stub files so the registry compiles. All but `StringField` can be 10-line placeholders overwritten in Tasks 14–17.

`frontend/src/components/form/fields/StringField.tsx`:

```tsx
import { forwardRef } from "react";
import { Input } from "@/components/ui/input";

export interface FieldProps {
  name: string;
  schema: Record<string, unknown>;
  register: any;
  error?: string;
}

export const StringField = forwardRef<HTMLInputElement, FieldProps>(function StringField(
  { name, schema, register, error },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input id={name} ref={ref} {...register(name)} />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
StringField.displayName = "StringField";
```

Placeholders (replace these entirely in the later tasks):

```tsx
// NumberField.tsx, BooleanField.tsx, DateField.tsx, EnumField.tsx
// Each just re-exports the StringField type to keep the registry typecheck-clean.
export { StringField as NumberField } from "./StringField";
// etc.
```

Do NOT ship those stubs — create them only to make TypeScript happy until Tasks 14-17 replace them. Commit the full implementations per task.

Actually, create the four placeholders inline within this task so the registry is fully typed now, and each subsequent task rewrites one:

```tsx
// NumberField.tsx
import { StringField } from "./StringField";
export const NumberField = StringField;
NumberField.displayName = "NumberField";

// BooleanField.tsx
import { StringField } from "./StringField";
export const BooleanField = StringField;
BooleanField.displayName = "BooleanField";

// DateField.tsx
import { StringField } from "./StringField";
export const DateField = StringField;
DateField.displayName = "DateField";

// EnumField.tsx
import { StringField } from "./StringField";
export const EnumField = StringField;
EnumField.displayName = "EnumField";
```

- [ ] **Step 4: Implement `FieldRegistry.ts`**

Create `frontend/src/components/form/FieldRegistry.ts`:

```ts
import type { ComponentType } from "react";
import { StringField, type FieldProps } from "./fields/StringField";
import { NumberField } from "./fields/NumberField";
import { BooleanField } from "./fields/BooleanField";
import { DateField } from "./fields/DateField";
import { EnumField } from "./fields/EnumField";

export type { FieldProps };
export type FieldComponent = ComponentType<FieldProps>;

const byType: Record<string, FieldComponent> = {
  string: StringField,
  number: NumberField,
  integer: NumberField,
  boolean: BooleanField,
};

const byWidget: Record<string, FieldComponent> = {
  date: DateField,
  enum: EnumField,
};

export function resolveFieldComponent(schema: Record<string, unknown>): FieldComponent {
  const widget = schema["x-widget"];
  if (typeof widget === "string" && byWidget[widget]) return byWidget[widget];
  if (Array.isArray(schema.enum)) return EnumField;

  const t = schema.type;
  if (typeof t === "string" && byType[t]) return byType[t];
  throw new Error(`Unsupported schema for field: ${JSON.stringify(schema)}`);
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/FieldRegistry.test.ts
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/form/
git commit -m "feat(form): FieldRegistry + StringField (placeholders for the other four)"
```

---

### Task 14: `NumberField`

**Files:**
- Modify (replace): `frontend/src/components/form/fields/NumberField.tsx`
- Create: `frontend/src/components/form/__tests__/NumberField.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/form/__tests__/NumberField.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useForm } from "react-hook-form";
import { NumberField } from "../fields/NumberField";

function Harness({ name, schema }: { name: string; schema: any }) {
  const { register } = useForm();
  return <NumberField name={name} schema={schema} register={register} />;
}

describe("NumberField", () => {
  it("renders an input[type=number] with the field title", () => {
    render(<Harness name="age" schema={{ type: "number", title: "Age" }} />);
    const input = screen.getByLabelText("Age");
    expect(input).toHaveAttribute("type", "number");
  });

  it("applies min/max from schema", () => {
    render(<Harness name="age" schema={{ type: "number", title: "Age", minimum: 0, maximum: 120 }} />);
    const input = screen.getByLabelText("Age");
    expect(input).toHaveAttribute("min", "0");
    expect(input).toHaveAttribute("max", "120");
  });
});
```

- [ ] **Step 2: Run — expected fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/NumberField.test.tsx
```

Expected: fail (NumberField is the StringField placeholder, renders text input).

- [ ] **Step 3: Implement**

Replace `frontend/src/components/form/fields/NumberField.tsx` with:

```tsx
import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import type { FieldProps } from "./StringField";

export const NumberField = forwardRef<HTMLInputElement, FieldProps>(function NumberField(
  { name, schema, register, error },
  ref,
) {
  const min = schema.minimum as number | undefined;
  const max = schema.maximum as number | undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input
        id={name}
        type="number"
        ref={ref}
        {...register(name, { valueAsNumber: true })}
        {...(min !== undefined ? { min } : {})}
        {...(max !== undefined ? { max } : {})}
      />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
NumberField.displayName = "NumberField";
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/NumberField.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/form/fields/NumberField.tsx frontend/src/components/form/__tests__/NumberField.test.tsx
git commit -m "feat(form): NumberField"
```

---

### Task 15: `BooleanField`

**Files:**
- Modify (replace): `frontend/src/components/form/fields/BooleanField.tsx`
- Create: `frontend/src/components/form/__tests__/BooleanField.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/form/__tests__/BooleanField.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { BooleanField } from "../fields/BooleanField";

function Harness({ name, schema }: { name: string; schema: any }) {
  const { register } = useForm();
  return <BooleanField name={name} schema={schema} register={register} />;
}

describe("BooleanField", () => {
  it("renders a checkbox with the field title", () => {
    render(<Harness name="agreed" schema={{ type: "boolean", title: "Agree" }} />);
    expect(screen.getByRole("checkbox", { name: "Agree" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expected fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/BooleanField.test.tsx
```

Expected: fail.

- [ ] **Step 3: Implement**

Replace `frontend/src/components/form/fields/BooleanField.tsx` with:

```tsx
import { forwardRef } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import type { FieldProps } from "./StringField";

export const BooleanField = forwardRef<HTMLButtonElement, FieldProps>(function BooleanField(
  { name, schema, register, error },
  ref,
) {
  const { onChange, ...rest } = register(name);
  return (
    <div className="flex items-center gap-2">
      <Checkbox
        id={name}
        ref={ref}
        {...rest}
        onCheckedChange={(checked: boolean) =>
          onChange({ target: { name, value: checked } })
        }
      />
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
BooleanField.displayName = "BooleanField";
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/BooleanField.test.tsx
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/form/fields/BooleanField.tsx frontend/src/components/form/__tests__/BooleanField.test.tsx
git commit -m "feat(form): BooleanField"
```

---

### Task 16: `DateField`

**Files:**
- Modify (replace): `frontend/src/components/form/fields/DateField.tsx`
- Create: `frontend/src/components/form/__tests__/DateField.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/form/__tests__/DateField.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { DateField } from "../fields/DateField";

function Harness({ name, schema }: { name: string; schema: any }) {
  const { register } = useForm();
  return <DateField name={name} schema={schema} register={register} />;
}

describe("DateField", () => {
  it("renders an input[type=date] with the field title", () => {
    render(<Harness name="startsOn" schema={{ type: "string", title: "Starts on", "x-widget": "date" }} />);
    const input = screen.getByLabelText("Starts on");
    expect(input).toHaveAttribute("type", "date");
  });
});
```

- [ ] **Step 2: Run — expected fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/DateField.test.tsx
```

Expected: fail.

- [ ] **Step 3: Implement**

Replace `frontend/src/components/form/fields/DateField.tsx` with:

```tsx
import { forwardRef } from "react";
import { Input } from "@/components/ui/input";
import type { FieldProps } from "./StringField";

export const DateField = forwardRef<HTMLInputElement, FieldProps>(function DateField(
  { name, schema, register, error },
  ref,
) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <Input id={name} type="date" ref={ref} {...register(name)} />
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
DateField.displayName = "DateField";
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/DateField.test.tsx
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/form/fields/DateField.tsx frontend/src/components/form/__tests__/DateField.test.tsx
git commit -m "feat(form): DateField"
```

---

### Task 17: `EnumField`

**Files:**
- Modify (replace): `frontend/src/components/form/fields/EnumField.tsx`
- Create: `frontend/src/components/form/__tests__/EnumField.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/form/__tests__/EnumField.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm } from "react-hook-form";
import { EnumField } from "../fields/EnumField";

function Harness({ name, schema }: { name: string; schema: any }) {
  const { register } = useForm();
  return <EnumField name={name} schema={schema} register={register} />;
}

describe("EnumField", () => {
  it("renders a combobox with the provided enum values", () => {
    render(
      <Harness
        name="status"
        schema={{ type: "string", title: "Status", enum: ["draft", "open", "closed"] }}
      />,
    );
    expect(screen.getByRole("combobox", { name: "Status" })).toBeInTheDocument();
    // Options are rendered inside the native <select> fallback used in tests.
    expect(screen.getByRole("option", { name: "draft" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "open" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "closed" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expected fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/EnumField.test.tsx
```

Expected: fail.

- [ ] **Step 3: Implement**

Replace `frontend/src/components/form/fields/EnumField.tsx` with:

```tsx
import { forwardRef } from "react";
import type { FieldProps } from "./StringField";

/**
 * Test-friendly EnumField using a native <select>. shadcn's Select uses Radix
 * portals that are painful in jsdom; for Plan 2 we ship the native element and
 * layer shadcn styling on top. Switching to the Radix component is a later cosmetic change.
 */
export const EnumField = forwardRef<HTMLSelectElement, FieldProps>(function EnumField(
  { name, schema, register, error },
  ref,
) {
  const values = (schema.enum as string[] | undefined) ?? [];
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={name} className="text-sm font-medium">
        {(schema.title as string) ?? name}
      </label>
      <select
        id={name}
        aria-label={(schema.title as string) ?? name}
        ref={ref}
        {...register(name)}
        className="h-9 rounded-md border border-input bg-background px-3 text-sm"
      >
        {values.map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </select>
      {error && <span role="alert" className="text-sm text-red-600">{error}</span>}
    </div>
  );
});
EnumField.displayName = "EnumField";
```

Note: this uses a raw `<select>` on purpose (see comment) — it is NOT the same anti-pattern as hand-rolled form inputs because it lives inside a `FieldRegistry`-dispatched component, which is the sanctioned entry point. Plan 3+ may swap to `@/components/ui/select`.

- [ ] **Step 4: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/EnumField.test.tsx
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/form/fields/EnumField.tsx frontend/src/components/form/__tests__/EnumField.test.tsx
git commit -m "feat(form): EnumField (native select pending shadcn wiring in Plan 3+)"
```

---

### Task 18: `FormRenderer` + ajv resolver

**Files:**
- Create: `frontend/src/components/form/resolver.ts`
- Create: `frontend/src/components/form/FormRenderer.tsx`
- Create: `frontend/src/components/form/__tests__/FormRenderer.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/form/__tests__/FormRenderer.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FormRenderer } from "../FormRenderer";

const simpleSchema = {
  type: "object",
  properties: {
    name: { type: "string", title: "Name" },
    age: { type: "number", title: "Age", minimum: 0 },
    active: { type: "boolean", title: "Active" },
  },
  required: ["name"],
};

describe("FormRenderer", () => {
  it("renders each field from the schema", () => {
    render(
      <FormRenderer schema={simpleSchema} onSubmit={() => {}}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.getByLabelText("Age")).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Active" })).toBeInTheDocument();
  });

  it("blocks submit when required field is empty", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={simpleSchema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("calls onSubmit with typed values when valid", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={simpleSchema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("Name"), "Ada");
    await userEvent.type(screen.getByLabelText("Age"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Ada", age: 40 }),
      expect.anything(),
    );
  });

  it("runs x-rules (mustMatch)", async () => {
    const schema = {
      type: "object",
      properties: {
        a: { type: "string", title: "A" },
        b: { type: "string", title: "B" },
      },
      mustMatch: { a: "a", b: "b" },
    };
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("A"), "x");
    await userEvent.type(screen.getByLabelText("B"), "y");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run — expected fail**

```bash
cd frontend && npx vitest run src/components/form/__tests__/FormRenderer.test.tsx
```

Expected: fail — FormRenderer missing.

- [ ] **Step 3: Implement the resolver**

Create `frontend/src/components/form/resolver.ts`:

```ts
import { ajvResolver } from "@hookform/resolvers/ajv";
import { ajv } from "@/lib/ajv";

export function makeResolver(schema: object) {
  // @hookform/resolvers/ajv accepts an Ajv instance via the third arg.
  return ajvResolver(schema as never, {}, { mode: "sync", ajv: ajv as never });
}
```

If the installed `@hookform/resolvers` version exposes a slightly different signature, adjust to its docs — the only invariant is that the shared `ajv` singleton is reused.

- [ ] **Step 4: Implement `FormRenderer.tsx`**

Create `frontend/src/components/form/FormRenderer.tsx`:

```tsx
import { type ReactNode, useMemo } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { makeResolver } from "./resolver";
import { resolveFieldComponent } from "./FieldRegistry";

export interface FormRendererProps<T extends Record<string, unknown>> {
  schema: Record<string, unknown>;
  defaultValues?: Partial<T>;
  onSubmit: (values: T, helpers: { setFieldErrors: (e: Record<string, string>) => void }) => void | Promise<void>;
  children?: ReactNode;
}

export function FormRenderer<T extends Record<string, unknown>>(
  props: FormRendererProps<T>,
): JSX.Element {
  const { schema, defaultValues, onSubmit, children } = props;
  const resolver = useMemo(() => makeResolver(schema), [schema]);

  const methods = useForm<T>({
    resolver,
    defaultValues: defaultValues as never,
    mode: "onSubmit",
  });

  const properties = (schema.properties ?? {}) as Record<string, Record<string, unknown>>;

  const setFieldErrors = (errors: Record<string, string>) => {
    for (const [name, message] of Object.entries(errors)) {
      methods.setError(name as never, { message, type: "server" });
    }
  };

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={methods.handleSubmit((values) => onSubmit(values, { setFieldErrors }))}
        className="flex flex-col gap-4"
      >
        {Object.entries(properties).map(([name, fieldSchema]) => {
          const Comp = resolveFieldComponent(fieldSchema);
          return (
            <Comp
              key={name}
              name={name}
              schema={fieldSchema}
              register={methods.register}
              error={methods.formState.errors[name as never]?.message as string | undefined}
            />
          );
        })}
        {children}
      </form>
    </FormProvider>
  );
}
```

- [ ] **Step 5: Run tests**

```bash
cd frontend && npx vitest run src/components/form/__tests__/
```

Expected: every form test file passes (FormRenderer 4, FieldRegistry 3, and the four field tests pass too).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/form/
git commit -m "feat(form): FormRenderer + ajv resolver wired to the singleton"
```

---

## Phase E — Frontend integration (1 task)

### Task 19: End-to-end MSW integration test

**Files:**
- Create: `frontend/src/lib/__tests__/primitives.integration.test.tsx`
- Modify: `frontend/src/test-setup.ts` (import MSW server if not already)

- [ ] **Step 1: Write integration test**

Create `frontend/src/lib/__tests__/primitives.integration.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    newPassword: { type: "string", title: "New password" },
    confirm: { type: "string", title: "Confirm" },
  },
  required: ["newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
};

const server = setupServer(
  http.post("/api/v1/password-reset", async () =>
    HttpResponse.json(
      {
        type: "about:blank",
        title: "Unprocessable Entity",
        status: 422,
        detail: "validation failed",
        code: "auth.weak-password",
        errors: [{ field: "newPassword", code: "weak", message: "too short" }],
      },
      { status: 422, headers: { "content-type": "application/problem+json" } },
    ),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("primitives integration", () => {
  it("ajv blocks submit when passwords don't match", async () => {
    const onSubmit = vi.fn();
    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("New password"), "abcdef");
    await userEvent.type(screen.getByLabelText("Confirm"), "zzzzzz");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("surfaces server-side field errors via setFieldErrors", async () => {
    const onSubmit = async (
      values: Record<string, string>,
      { setFieldErrors }: { setFieldErrors: (e: Record<string, string>) => void },
    ) => {
      try {
        await client.post("/password-reset", values);
      } catch (err) {
        if (isProblemDetails(err) && err.errors) {
          setFieldErrors(
            Object.fromEntries(
              err.errors.map((e) => [e.field, e.message ?? e.code]),
            ),
          );
        }
      }
    };

    render(
      <FormRenderer schema={schema} onSubmit={onSubmit}>
        <button type="submit">Save</button>
      </FormRenderer>,
    );
    await userEvent.type(screen.getByLabelText("New password"), "match1");
    await userEvent.type(screen.getByLabelText("Confirm"), "match1");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText("too short")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Ensure MSW is usable in tests**

Check `frontend/src/test-setup.ts`. If it does not already register `msw/node`, add:

```ts
// top of test-setup.ts (if not present)
import "@testing-library/jest-dom/vitest";
```

No further setup needed — the test file above creates its own server instance.

- [ ] **Step 3: Run test**

```bash
cd frontend && npx vitest run src/lib/__tests__/primitives.integration.test.tsx
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/__tests__/primitives.integration.test.tsx frontend/src/test-setup.ts
git commit -m "test(plan2): MSW integration — ajv block + server FieldError surfacing"
```

---

## Phase F — L1 audits (4 tasks)

### Task 20: `audit_httpexception.sh`

**Files:**
- Create: `scripts/audit/audit_httpexception.sh`

- [ ] **Step 1: Implement**

Create `scripts/audit/audit_httpexception.sh`:

```bash
#!/usr/bin/env bash
# Fails if any file under backend/app/modules/ raises bare HTTPException.
# Endpoints must raise ProblemDetails instead.
set -u

PATH_SCAN="backend/app/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

MATCHES=$(grep -rnE 'raise[[:space:]]+HTTPException\(' "$PATH_SCAN" --include='*.py' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found bare HTTPException raises — use ProblemDetails instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
```

- [ ] **Step 2: chmod and test**

```bash
chmod +x scripts/audit/audit_httpexception.sh
bash scripts/audit/audit_httpexception.sh
echo "exit=$?"
```

Expected: `exit=0` (no modules/ code yet).

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_httpexception.sh
git commit -m "audit: forbid bare HTTPException in modules/"
```

---

### Task 21: `audit_scalars_all.sh`

**Files:**
- Create: `scripts/audit/audit_scalars_all.sh`

- [ ] **Step 1: Implement**

Create `scripts/audit/audit_scalars_all.sh`:

```bash
#!/usr/bin/env bash
# Fails if any router.py in modules/ calls .scalars().all() or bare .all() on a Select.
# List endpoints must use paginate().
set -u

PATH_SCAN="backend/app/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

MATCHES=$(grep -rnE '\.scalars\(\)\.all\(\)|\.all\(\)[[:space:]]*$' "$PATH_SCAN" --include='router.py' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found unpaginated .all() calls in router.py — use paginate() instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
```

- [ ] **Step 2: chmod and test**

```bash
chmod +x scripts/audit/audit_scalars_all.sh
bash scripts/audit/audit_scalars_all.sh
echo "exit=$?"
```

Expected: `exit=0`.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_scalars_all.sh
git commit -m "audit: forbid unpaginated .all() in module routers"
```

---

### Task 22: `audit_handwritten_form.sh`

**Files:**
- Create: `scripts/audit/audit_handwritten_form.sh`

- [ ] **Step 1: Implement**

Create `scripts/audit/audit_handwritten_form.sh`:

```bash
#!/usr/bin/env bash
# Fails if any module page renders form controls directly instead of via <FormRenderer>.
# Field components inside components/form/fields/ are exempt.
set -u

PATH_SCAN="frontend/src/modules"
[ -d "$PATH_SCAN" ] || { exit 0; }

# Patterns that indicate a hand-rolled form field in a business page.
PATTERN='<input[[:space:]]|<textarea[[:space:]]|<TextField[[:space:]]|<Input[[:space:]]'

MATCHES=$(grep -rnE "$PATTERN" "$PATH_SCAN" --include='*.tsx' 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Found hand-rolled form controls in modules/ — use <FormRenderer /> instead:"
    echo "$MATCHES"
    exit 1
fi
exit 0
```

- [ ] **Step 2: chmod and test**

```bash
chmod +x scripts/audit/audit_handwritten_form.sh
bash scripts/audit/audit_handwritten_form.sh
echo "exit=$?"
```

Expected: `exit=0`.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_handwritten_form.sh
git commit -m "audit: forbid hand-rolled form controls in frontend modules/"
```

---

### Task 23: Wire the three new audits into `run_all.sh`

**Files:**
- Modify: `scripts/audit/run_all.sh`

- [ ] **Step 1: Edit `run_all.sh`**

Append three new `run` lines after the existing `run "pagination-fe"` line:

```bash
run "httpexception"   bash scripts/audit/audit_httpexception.sh
run "scalars-all"     bash scripts/audit/audit_scalars_all.sh
run "handwritten-form" bash scripts/audit/audit_handwritten_form.sh
```

Target file looks like:

```bash
run "except"           bash scripts/audit/audit_except.sh
run "todo"             bash scripts/audit/audit_todo.sh
run "mock-leak"        bash scripts/audit/audit_mock_leak.sh
run "json-schema"      bash scripts/audit/audit_json_schema.sh
run "mui-imports"      bash scripts/audit/audit_mui_imports.sh
run "pagination-fe"    bash scripts/audit/audit_pagination_fe.sh
run "httpexception"    bash scripts/audit/audit_httpexception.sh
run "scalars-all"      bash scripts/audit/audit_scalars_all.sh
run "handwritten-form" bash scripts/audit/audit_handwritten_form.sh
```

(Keep the existing Python audit block untouched.)

- [ ] **Step 2: Run the full audit suite**

```bash
bash scripts/audit/run_all.sh
```

Expected: every check prints `PASS`, final line `✔ All L1 audits passed.`, exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/run_all.sh
git commit -m "audit: register plan2 audits in run_all.sh"
```

---

## Phase G — Conventions docs (4 tasks)

Each of these tasks APPENDS a concrete, code-bearing example to an existing doc — do not remove or rewrite existing sections. Match the doc's existing voice and formatting (these docs are the agent-facing contract).

### Task 24: Append BaseSchema + rules examples to `docs/conventions/01-schema-validation.md`

- [ ] **Step 1: Read the existing doc**

```bash
cat docs/conventions/01-schema-validation.md
```

- [ ] **Step 2: Append a new section at the end**

Append the following (preserve existing content):

````markdown

## Concrete primitives (shipped in Plan 2)

### `BaseSchema`

```python
from app.core.schemas import BaseSchema

class UserRead(BaseSchema):
    id: int
    email: str
    created_at: datetime
```

- camelCase at the boundary (`createdAt`).
- Accepts both `snake_case` and `camelCase` on input.
- Reads from SQLAlchemy instances.
- `datetime` with UTC offset is normalized to `Z`.

### Cross-field rules

```python
from app.core.form_rules import must_match, date_order
from app.core.schemas import BaseSchema

class PasswordReset(BaseSchema):
    new_password: str
    confirm: str
    __rules__ = [must_match(a="new_password", b="confirm")]

class DateRange(BaseSchema):
    starts_on: date
    ends_on: date
    __rules__ = [date_order(start="starts_on", end="ends_on")]
```

The `__rules__` attribute is consumed by `BaseSchema`: each entry emits `x-rules` in `model_json_schema()` (for the frontend) and attaches a `@model_validator` (for the backend). Only names registered in `FormRuleRegistry` may be used.

Adding a new rule? Add it to `backend/app/core/form_rules.py` AND to `frontend/src/lib/form-rules.ts` in the same PR.
````

- [ ] **Step 3: Commit**

```bash
git add docs/conventions/01-schema-validation.md
git commit -m "docs(conventions): add Plan 2 BaseSchema and rules examples"
```

---

### Task 25: Append guards example to `docs/conventions/02-service-guards.md`

- [ ] **Step 1: Append**

````markdown

## Concrete guards (shipped in Plan 2)

### Declarative attachment

```python
from sqlalchemy.orm import Mapped, mapped_column
from app.core.guards import NoDependents

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)

    __guards__ = {
        "delete": [
            NoDependents("users", "department_id"),
            NoDependents("roles", "default_department_id"),
        ],
    }
```

### Service layer

```python
from app.core.guards import GuardViolationError, ServiceBase
from app.core.errors import ProblemDetails, GuardViolationCtx
from app.modules.department.models import Department

class DepartmentService(ServiceBase):
    model = Department

    async def delete_safe(self, session, instance):
        try:
            await self.delete(session, instance)
        except GuardViolationError as e:
            raise ProblemDetails(
                code="department.has-dependents",
                status=409,
                detail="Cannot delete a department with dependents.",
                guard_violation=GuardViolationCtx(guard="NoDependents", params=e.ctx),
            )
```

DB-level `ON DELETE RESTRICT` is the belt; guards are the braces. Keep both.
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/02-service-guards.md
git commit -m "docs(conventions): add Plan 2 ServiceBase and NoDependents example"
```

---

### Task 26: Append form example to `docs/conventions/04-forms.md`

- [ ] **Step 1: Append**

````markdown

## Concrete renderer (shipped in Plan 2)

```tsx
import { FormRenderer } from "@/components/form/FormRenderer";
import { client } from "@/api/client";
import { isProblemDetails } from "@/lib/problem-details";

const schema = {
  type: "object",
  properties: {
    newPassword: { type: "string", title: "New password" },
    confirm: { type: "string", title: "Confirm" },
  },
  required: ["newPassword", "confirm"],
  mustMatch: { a: "newPassword", b: "confirm" },
};

export function PasswordResetForm() {
  return (
    <FormRenderer
      schema={schema}
      onSubmit={async (values, { setFieldErrors }) => {
        try {
          await client.post("/password-reset", values);
        } catch (err) {
          if (isProblemDetails(err) && err.errors) {
            setFieldErrors(Object.fromEntries(err.errors.map((e) => [e.field, e.message ?? e.code])));
          }
        }
      }}
    >
      <button type="submit">Save</button>
    </FormRenderer>
  );
}
```

- Every form in `modules/` uses `<FormRenderer>`. No hand-rolled `<input>` trees.
- `x-rules` in the schema (emitted automatically by backend `__rules__`) are enforced by the shared Ajv singleton.
- Server-side `FieldError`s from a `ProblemDetails` response are surfaced inline via `setFieldErrors`.
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/04-forms.md
git commit -m "docs(conventions): add Plan 2 FormRenderer + setFieldErrors example"
```

---

### Task 27: Append pagination + Problem Details example to `docs/conventions/05-api-contract.md`

- [ ] **Step 1: Append**

````markdown

## Concrete endpoint shapes (shipped in Plan 2)

### List endpoints return `Page[T]`

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
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
// client has:
//   baseURL        — VITE_API_BASE_URL (defaults to /api/v1)
//   interceptor    — converts Problem Details responses into typed rejects
// Never `new axios.create()` elsewhere. Never `fetch()`.
const { data } = await client.get<Page<UserRead>>("/users", { params: { page: 1, size: 20 } });
```
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/05-api-contract.md
git commit -m "docs(conventions): add Plan 2 Page[T] + ProblemDetails examples"
```

---

## Phase H — Smoke verification (1 task)

### Task 28: Run the full gate and tag `v0.2.0-primitives`

- [ ] **Step 1: Backend suite**

```bash
cd backend && uv run pytest -v
```

Expected: every test in `tests/core/` plus `test_healthz.py` and `test_primitives_integration.py` passes. Zero failures. Exit 0.

- [ ] **Step 2: Backend lint + ruff format check**

```bash
cd backend && uv run ruff check . && uv run ruff format --check .
```

Expected: both exit 0. If format-check fails, run `uv run ruff format .` and commit the result.

- [ ] **Step 3: Frontend suite**

```bash
cd frontend && npm test -- --run
```

Expected: all tests pass.

- [ ] **Step 4: Frontend typecheck + lint**

```bash
cd frontend && npm run typecheck && npm run lint
```

Expected: both exit 0.

- [ ] **Step 5: L1 audit suite**

```bash
bash scripts/audit/run_all.sh
```

Expected: `✔ All L1 audits passed.`, exit 0.

- [ ] **Step 6: Invoke the convention-auditor subagent**

Dispatch `.claude/agents/convention-auditor.md` against the diff since `v0.1.0-foundation`:

```bash
git diff v0.1.0-foundation..HEAD --stat
```

Expected verdict: `VERDICT: PASS`. If the auditor flags a deviation from a convention, fix inline; do NOT tag until the verdict is PASS.

- [ ] **Step 7: Tag**

```bash
git tag -a v0.2.0-primitives -m "Plan 2 complete: core primitives ship. Ready for Plan 3 (auth)."
git tag -l v0.2.0-primitives
```

Expected: tag listed.

- [ ] **Step 8: Final state check**

```bash
git log --oneline v0.1.0-foundation..HEAD | wc -l
```

Expected: roughly 26–32 commits (one per task + small touch-ups). No uncommitted files.

---

## Invariants reminder

If any step in a later plan (Plan 3+) violates one of these, stop and fix:

1. Every request/response model inherits `BaseSchema`.
2. No bare `HTTPException`; always `ProblemDetails`.
3. List endpoints return `Page[T]` and use `paginate()`.
4. Cross-field validation goes through the registry (`__rules__`), never a free-form `@model_validator`.
5. Delete/transition guards live on the model via `__guards__`.
6. Forms always flow through `<FormRenderer>`.
7. All HTTP goes through `api/client.ts`.
8. Tokens live in `sessionStorage` / HttpOnly cookies, never `localStorage`.
9. Ajv is the only frontend validator.
10. A rule or guard must be registered on BOTH sides before it may appear in a schema.
