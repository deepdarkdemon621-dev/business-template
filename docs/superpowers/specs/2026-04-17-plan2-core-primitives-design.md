# Plan 2 — Core Primitives (Design Spec)

**Status**: Design — awaiting implementation plan
**Supersedes**: none
**Inherits constraints from**: `2026-04-15-business-template-core-design.md` §5.1, §5.2, §5.4, §5.5
**Date**: 2026-04-17
**Audience**: Any agent (human or AI) implementing Plan 2, or building business modules in Plan 3+. This document is the authoritative contract for the primitives listed below. If the code disagrees with this spec, the spec is correct and the code is a bug.

---

## 1. Purpose

Plan 2 delivers the library-layer primitives that every business module in Plan 3+ will depend on. It produces **no endpoints, no DB tables, no user-facing features** — only reusable infrastructure:

- Response schema base (camelCase boundary, ISO 8601 timestamps)
- RFC 7807 Problem Details error model
- Server-side pagination (query dependency, page helper, endpoint base)
- Service guard registry (declarative invariants on mutations)
- Form-rule registry (cross-field validation vocabulary)
- Frontend form renderer (`FormRenderer` + `FieldRegistry` + ajv integration)
- Axios client with Problem Details parsing

Plan 2 does **not** touch authentication, RBAC, or any concrete business domain. `current_user`, `require_perm`, `apply_scope` are explicitly out of scope — they arrive in Plan 3 (auth) and Plan 4 (RBAC).

## 2. Scope

### 2.1 In scope

Backend (`backend/app/core/`):
- `schemas.py` — `BaseSchema`
- `errors.py` — `ProblemDetails` exception + FastAPI exception handler + `application/problem+json` response
- `pagination.py` — `PageQuery`, `Page[T]`, `PaginatedEndpoint`, `paginate()`
- `guards.py` — `ServiceGuardRegistry`, `GuardViolationError`, `NoDependents`, `StateAllows`, `ServiceBase`
- `form_rules.py` — `FormRuleRegistry`, `dateOrder`, `mustMatch`, rule-to-validator decorator

Frontend (`frontend/src/`):
- `lib/ajv.ts` — singleton Ajv instance
- `lib/form-rules.ts` — `dateOrder` and `mustMatch` as Ajv keywords (signatures mirror backend)
- `lib/problem-details.ts` — typed Problem Details parser
- `lib/pagination.ts` — `Page<T>`, `PageQuery` types
- `api/client.ts` — Axios singleton with Problem Details interceptor
- `components/form/FormRenderer.tsx`, `FieldRegistry.ts`
- `components/form/fields/` — `StringField`, `NumberField`, `BooleanField`, `DateField`, `EnumField`

Testing:
- Unit tests for every primitive
- Two integration-test files (one backend, one frontend) that wire all primitives against mocks / MSW

Audit:
- Three new L1 audit scripts (`audit_httpexception.sh`, `audit_scalars_all.sh`, `audit_handwritten_form.sh`)

Convention updates:
- Code examples appended to `docs/conventions/01`, `02`, `04`, `05` once primitives are real

### 2.2 Out of scope (and why)

| Deferred item | Target plan | Reason |
|---|---|---|
| `require_perm`, `apply_scope`, `/me/permissions` | Plan 4 (RBAC) | Depend on `current_user`, which comes from auth (Plan 3) |
| `SameDepartment` guard | Plan 4 | Needs `current_user` |
| File / Array / Object field components | Plan 5 (File) / later | Nested-form + attachment service complexity |
| `conditionalRequired`, `mutuallyExclusive`, `uniqueInList` rules | Just-in-time as Plan 3+ modules need them | Registry pattern makes this additive |
| `ImmutableAfter`, `NoActiveChildren` guards | Same | Registry pattern makes this additive |
| `audit_baseschema.sh`, `audit_guards_registered.sh`, `audit_xrules_vocab.sh` | Plan 3/4 | Need Python AST + real module code for accurate detection |
| Real-DB integration tests | Plan 3+ | Plan 2 primitives are testable with mocked sessions |

## 3. Architecture

```
backend/app/core/
├── schemas.py        # BaseSchema
├── errors.py         # ProblemDetails + handler
├── pagination.py     # PageQuery, Page[T], PaginatedEndpoint, paginate()
├── guards.py         # ServiceGuardRegistry, GuardViolationError, ServiceBase
└── form_rules.py     # FormRuleRegistry + @with_rules

frontend/src/
├── lib/
│   ├── ajv.ts             # single Ajv instance (ajv-formats + keywords)
│   ├── form-rules.ts      # dateOrder, mustMatch as Ajv keywords
│   ├── problem-details.ts # typed parser
│   ├── pagination.ts      # Page<T>, PageQuery types
│   └── ...
├── api/
│   └── client.ts          # Axios + ProblemDetails interceptor (401 stub → Plan 3)
└── components/form/
    ├── FormRenderer.tsx   # schema → RHF + ajv resolver → <Field>
    ├── FieldRegistry.ts   # JSON Schema type → component, x-widget override
    └── fields/
        ├── StringField.tsx   BooleanField.tsx   DateField.tsx
        ├── NumberField.tsx   EnumField.tsx
```

**Guiding constraints**:

1. Primitives are **pure libraries**. They do not boot the app, do not open DB connections, do not read configuration at import time.
2. Anything DB-touching (`paginate`, `NoDependents`) takes an `AsyncSession` as a parameter. Tests pass mocks.
3. The frontend `ajv` instance is a **singleton**. Every form uses the same instance. Keywords are registered once, at module load.
4. Backend and frontend rule signatures are **symmetric**. `mustMatch(a, b)` means the same thing in Pydantic and in Ajv. This is enforced by the cross-reference audit (Plan 3+) and by code review.
5. `core/` code **must not import** from `app/modules/`. Core is a leaf dependency.

## 4. Backend Primitives

### 4.1 `BaseSchema` (`core/schemas.py`)

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base class for every request and response Pydantic model.

    - Serializes to camelCase at the API boundary (`created_at` → `createdAt`).
    - Accepts both camelCase and snake_case on input (`populate_by_name=True`).
    - Reads directly from SQLAlchemy instances (`from_attributes=True`).
    - Emits ISO 8601 datetimes with explicit UTC offset, normalized to `Z` suffix.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
```

**Constraints**:
- Every response model in `modules/*/schemas.py` MUST inherit from `BaseSchema`. (Plan 3+ audit will enforce.)
- Do NOT override `alias_generator` per model. If a field needs a different alias, use `Field(alias=...)`.
- Timestamps: `datetime` fields are serialized to ISO 8601 with an explicit UTC offset. `BaseSchema` normalizes `+00:00` to `Z` (via a model serializer or Annotated `datetime` type — choice punted to implementation; contract is the wire format).

**Usage**:
```python
class UserRead(BaseSchema):
    id: int
    email: str
    created_at: datetime
# JSON output: {"id": 1, "email": "...", "createdAt": "2026-04-17T10:00:00Z"}
```

### 4.2 `ProblemDetails` (`core/errors.py`)

```python
class FieldError(BaseSchema):
    field: str          # dotted path, e.g. "addresses.0.zip"
    code: str           # machine-readable: "required", "max_length", ...
    message: str | None = None

class GuardViolationCtx(BaseSchema):
    guard: str          # guard name, e.g. "NoDependents"
    params: dict[str, Any] = {}

class ProblemDetails(Exception):
    """RFC 7807 Problem Details. The only allowed error type in endpoints."""
    def __init__(
        self,
        *,
        code: str,                     # kebab-case, e.g. "user.not-found"
        status: int,                   # HTTP status
        detail: str,                   # human-readable message
        title: str | None = None,      # short, not localized
        errors: list[FieldError] | None = None,
        guard_violation: GuardViolationCtx | None = None,
    ) -> None: ...
```

FastAPI exception handler converts to:

```json
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "about:blank",
  "title": "Validation failed",
  "status": 422,
  "detail": "...",
  "code": "user.invalid-email",
  "errors": [{"field": "email", "code": "format", "message": "..."}]
}
```

**Constraints**:
- Endpoints MUST NOT raise bare `HTTPException`. Always raise `ProblemDetails`. (Audit: `audit_httpexception.sh`.)
- `code` is kebab-case with a resource prefix: `user.not-found`, `department.has-users`, `workflow.invalid-transition`.
- The set of codes is not centrally registered in Plan 2. Plan 4+ may add a registry.

**Usage**:
```python
raise ProblemDetails(
    code="department.has-users",
    status=409,
    detail="Cannot delete a department that still has users.",
    guard_violation=GuardViolationCtx(guard="NoDependents", params={"relation": "users"}),
)
```

### 4.3 Pagination (`core/pagination.py`)

```python
class PageQuery(BaseModel):
    """FastAPI query-param dependency.

    Attach to a list endpoint via `Depends()` or inherit `PaginatedEndpoint`.
    """
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)  # hard cap, server silently clamps
    sort: str | None = None   # e.g. "-created_at,name"
    q: str | None = None

class Page[T](BaseSchema):
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
    """Execute COUNT(*) over stmt, then LIMIT/OFFSET stmt, return a Page.

    The caller is responsible for applying filter/sort/search to `stmt`
    before passing it in. paginate only handles counting and slicing.
    """
```

**Constraints**:
- Endpoints MUST NOT call `.scalars().all()` or `.all()` on a select statement. Always use `paginate()`. (Audit: `audit_scalars_all.sh`.)
- List endpoints MUST declare their return type as `Page[ItemRead]`, not `list[ItemRead]`.
- `size > 100` is silently clamped to 100. Do not error; an AI that gets a too-large page just gets 100 rows.

**Usage**:
```python
@router.get("/users", response_model=Page[UserRead])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    pq: Annotated[PageQuery, Depends()],
) -> Page[UserRead]:
    stmt = select(User).order_by(User.id)
    return await paginate(session, stmt, pq)
```

### 4.4 Service Guards (`core/guards.py`)

```python
class GuardViolationError(Exception):
    """Raised inside a guard check. Service layer converts to ProblemDetails."""
    def __init__(self, code: str, ctx: dict[str, Any]) -> None: ...

class Guard(Protocol):
    async def check(self, session: AsyncSession, instance: Any) -> None: ...

class NoDependents:
    """Fails if any row in `relation` references instance.id via fk_col."""
    def __init__(self, relation: str, fk_col: str) -> None: ...
    async def check(self, session, instance) -> None: ...

class StateAllows:
    """Fails unless instance.<field> is in allowed."""
    def __init__(self, field: str, allowed: list[Any]) -> None: ...

class ServiceBase:
    """Base class for module services. Auto-runs model.__guards__ before mutations."""
    model: type[DeclarativeBase]

    async def delete(self, session: AsyncSession, instance) -> None:
        for guard in getattr(self.model, "__guards__", {}).get("delete", []):
            await guard.check(session, instance)
        await session.delete(instance)

    # Plan 3+ adds update(), etc.
```

**Declarative attachment** — guards live on the model:

```python
class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    ...
    __guards__ = {
        "delete": [
            NoDependents("users", "department_id"),
            NoDependents("roles", "default_department_id"),
        ],
    }
```

**Constraints**:
- Endpoints MUST NOT write `if await session.scalar(exists(...)): raise ProblemDetails(...)` ad hoc. Guards go on `__guards__`.
- Services MUST inherit `ServiceBase` (or future siblings) so guards run automatically.
- DB-level ON DELETE RESTRICT is the belt; guards are the braces. Both are required.

### 4.5 Form Rules (`core/form_rules.py`)

Cross-field validation vocabulary. Signatures are identical on backend (Pydantic validator) and frontend (Ajv keyword).

```python
# Rule factories — return (x-rules entry, validator function)
def date_order(*, start: str, end: str) -> RuleSpec: ...
def must_match(*, a: str, b: str) -> RuleSpec: ...

# Applied to a schema via __rules__ on a subclass:
class PasswordReset(BaseSchema):
    new_password: str
    confirm: str
    __rules__ = [must_match(a="new_password", b="confirm")]
```

A metaclass or `__init_subclass__` in `BaseSchema` consumes `__rules__`:
1. Merges `x-rules` entries into `model_config.json_schema_extra`, so `model_json_schema()` emits them for frontend Ajv.
2. Registers a `@model_validator(mode='after')` that runs the same checks on backend submit.

**x-rules JSON shape** (exactly what the frontend expects):

```json
{
  "x-rules": [
    {"name": "mustMatch", "params": {"a": "newPassword", "b": "confirm"}}
  ]
}
```

Note the camelCase — field names are converted to their API-boundary form when `x-rules` is emitted.

**Constraints**:
- Only names registered in `FormRuleRegistry` may appear in `x-rules`. (Plan 3+ audit: `audit_xrules_vocab.sh`.)
- Adding a new rule requires implementing it on BOTH sides (Python + Ajv keyword) in the same PR.
- Do NOT write free-form Pydantic `@model_validator` functions for cross-field checks. Use the registry.

### 4.6 Catalog of Plan 2 rules and guards

| Category | Name | Signature | Notes |
|---|---|---|---|
| Rule | `date_order` / `dateOrder` | `(start, end)` | end > start; end required iff start present |
| Rule | `must_match` / `mustMatch` | `(a, b)` | Any type, strict equality |
| Guard | `NoDependents` | `(relation, fk_col)` | Delete guard |
| Guard | `StateAllows` | `(field, allowed)` | State-machine guard |

More rules/guards arrive just-in-time in Plan 3+. Each addition is a small PR touching: `form_rules.py`, `form-rules.ts`, and a test pair.

## 5. Frontend Primitives

### 5.1 Ajv (`lib/ajv.ts`)

```ts
import Ajv from "ajv";
import addFormats from "ajv-formats";
import { registerRuleKeywords } from "./form-rules";

export const ajv = new Ajv({
  allErrors: true,
  strictSchema: false,   // permit x-rules and x-widget without schema errors
  useDefaults: true,
});
addFormats(ajv);
registerRuleKeywords(ajv);   // adds mustMatch, dateOrder
```

**Constraints**:
- Exactly one Ajv instance per app. Do not `new Ajv()` elsewhere.
- Do NOT add Zod / Yup. Ajv is the only schema validator.

### 5.2 Form rules (`lib/form-rules.ts`)

```ts
export function registerRuleKeywords(ajv: Ajv): void {
  ajv.addKeyword({
    keyword: "mustMatch",
    type: "object",
    errors: true,
    validate: function (this: any, params: { a: string; b: string }, data: any) {
      // reads camelCase keys — matches x-rules payload
      return data[params.a] === data[params.b];
    },
  });
  // dateOrder similarly
}
```

Rule signatures mirror the backend. Adding a new rule adds one keyword here and one Python factory on the backend.

### 5.3 Problem Details (`lib/problem-details.ts`)

```ts
export interface FieldError { field: string; code: string; message?: string }
export interface GuardViolationCtx { guard: string; params: Record<string, unknown> }
export interface ProblemDetails {
  type: string; title?: string; status: number; detail: string; code: string;
  errors?: FieldError[]; guardViolation?: GuardViolationCtx;
}

export function isProblemDetails(x: unknown): x is ProblemDetails { ... }
```

### 5.4 Pagination types (`lib/pagination.ts`)

```ts
export interface PageQuery { page?: number; size?: number; sort?: string; q?: string }
export interface Page<T> { items: T[]; total: number; page: number; size: number; hasNext: boolean }
```

Note `hasNext` — this is the camelCase form. Backend emits `hasNext` because of `alias_generator`.

### 5.5 Axios client (`api/client.ts`)

```ts
import axios, { AxiosError } from "axios";
import { isProblemDetails, ProblemDetails } from "@/lib/problem-details";

export const client = axios.create({ baseURL: "/api/v1" });

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError) => {
    const data = err.response?.data;
    if (isProblemDetails(data)) {
      // Plan 3 will extend this: if status === 401, try refresh; else redirect.
      // Plan 2 ships a stub: just reject with a ProblemDetails-typed error.
      return Promise.reject(data satisfies ProblemDetails);
    }
    return Promise.reject(err);
  }
);
```

**Constraints**:
- Only `api/client.ts` may call Axios directly. Every module imports `client` from here.
- Do NOT use `fetch()`. Do NOT call `axios.get()` with a new instance.
- Access tokens are injected here (Plan 3). Never read tokens in business code.
- Tokens are stored in `sessionStorage` or an HttpOnly cookie. NEVER `localStorage`.

### 5.6 FormRenderer (`components/form/FormRenderer.tsx`)

```tsx
interface FormRendererProps<T> {
  schema: JsonSchema;              // includes x-rules
  defaultValues?: DeepPartial<T>;
  onSubmit: (values: T) => Promise<void> | void;
  children?: React.ReactNode;      // e.g., a submit button
}

export function FormRenderer<T>(props: FormRendererProps<T>): JSX.Element { ... }
```

Behavior:
1. Pass schema to `ajvResolver(ajv, schema)` from `@hookform/resolvers/ajv`.
2. Walk schema `properties`; for each field, look up `FieldRegistry[type]` (or `x-widget` override), render with RHF `register`/`control`.
3. On submit: RHF + Ajv validate; on success, call `props.onSubmit(values)`.
4. Render server-side errors (from `ProblemDetails.errors`) inline under each field by `FieldError.field` path.

**Constraints**:
- Pages MUST NOT hand-roll forms with `<input>` / `<Input>` / `<TextField>`. (Audit: `audit_handwritten_form.sh`.)
- Pages MUST NOT call `useForm()` directly for submission validation — `FormRenderer` owns resolver choice.

### 5.7 FieldRegistry (`components/form/FieldRegistry.ts`)

```ts
export interface FieldProps { name: string; schema: JsonSchema; ... }
export type FieldComponent = React.FC<FieldProps>;

export const FieldRegistry: Record<string, FieldComponent> = {
  string: StringField,
  number: NumberField,
  integer: NumberField,
  boolean: BooleanField,
  // x-widget='date' → DateField; enum → EnumField; etc.
};

export function resolveFieldComponent(schema: JsonSchema): FieldComponent { ... }
```

**Plan 2 ships**: `StringField`, `NumberField`, `BooleanField`, `DateField`, `EnumField`.

**Plan 5 adds**: `FileField` (needs attachment service).

**Later**: `ArrayField`, `ObjectField` (nested forms — non-trivial, deliberately deferred).

All Field components MUST use primitives from `@/components/ui/` only. No direct Radix / shadcn imports in fields.

## 6. Testing

### 6.1 Unit tests

| File | Primitives covered |
|---|---|
| `backend/tests/core/test_schemas.py` | BaseSchema: camelCase serialization, `populate_by_name`, `from_attributes`, ISO 8601 UTC datetime |
| `backend/tests/core/test_errors.py` | `ProblemDetails` exception → handler → `application/problem+json` with correct shape |
| `backend/tests/core/test_pagination.py` | `paginate()` with mock session: count/offset/limit, `has_next` edge cases, `size > 100` clamp |
| `backend/tests/core/test_guards.py` | `NoDependents` / `StateAllows` on mock session; `ServiceBase.delete` auto-runs `__guards__` |
| `backend/tests/core/test_form_rules.py` | `must_match` / `date_order`: Pydantic validator fires; `x-rules` is present in `model_json_schema()` |
| `frontend/src/lib/__tests__/ajv.test.ts` | Singleton identity; keywords registered; `mustMatch` / `dateOrder` pass/fail |
| `frontend/src/components/form/__tests__/FormRenderer.test.tsx` | Each of 5 fields renders; submit calls `onSubmit` only when valid; inline server errors rendered |

### 6.2 Integration tests (single file each)

- `backend/tests/test_primitives_integration.py` — Wires a `FastAPI()` with a fake "items" resource. Router uses `PaginatedEndpoint`, `ServiceBase`, and `ProblemDetails`. Asserts: `GET /items?page=1&size=5` returns `Page[Item]` shape; `DELETE /items/1` triggers `NoDependents` → `guard_violation` in Problem Details body.
- `frontend/src/lib/__tests__/primitives.integration.test.tsx` — Renders a password-change form via `<FormRenderer>` with a `mustMatch` rule. MSW mocks a backend that returns a Problem Details with a `FieldError`. Asserts: Ajv blocks submit on mismatch; server errors render under the correct field.

Integration tests are **intentionally throwaway** — they exist to prove Plan 2 primitives compose. Plan 3's first real endpoint produces end-to-end tests that supersede them.

### 6.3 Testing discipline

- Async tests: `pytest-asyncio` with `asyncio_mode = "auto"`.
- Mock sessions: `unittest.mock.AsyncMock` configured to return seeded rows.
- MSW for frontend: per-test handlers, no global state.
- No real Postgres, no real Redis in Plan 2.

## 7. L1 audit additions

Three new scripts, all grep-based, added to `run_all.sh`:

| Script | Rule | Guard rail for |
|---|---|---|
| `audit_httpexception.sh` | `raise HTTPException(` is forbidden in `backend/app/modules/` | §4.2 |
| `audit_scalars_all.sh` | `.scalars().all()` and `.all()` are forbidden in `backend/app/modules/*/router.py` | §4.3 |
| `audit_handwritten_form.sh` | `<input ` / `<Input ` / `<textarea` / `<TextField` forbidden in `frontend/src/modules/*/*.tsx` | §5.6 |

Deferred to Plan 3+ (require AST):
- `audit_baseschema.sh` (response models inherit BaseSchema)
- `audit_guards_registered.sh` (models with DELETE endpoints have `__guards__['delete']`)
- `audit_xrules_vocab.sh` (every `x-rules` name is in FormRuleRegistry)

## 8. Conventions docs to update

After primitives ship, append concrete code examples to these agent-facing docs (so Plan 3+ agents see the real API):

- `docs/conventions/01-schema-validation.md` — BaseSchema usage, rule registration, `__rules__` pattern
- `docs/conventions/02-service-guards.md` — `ServiceBase` subclassing, `__guards__` declaration, `GuardViolationError` → `ProblemDetails` translation
- `docs/conventions/04-forms.md` — `<FormRenderer>` usage, ajv singleton, adding an `x-widget`
- `docs/conventions/05-api-contract.md` — `Page[T]` + `PaginatedEndpoint` usage, `ProblemDetails` codes, Axios client import

## 9. Task breakdown (estimate)

Roughly 29 tasks across 8 phases (final count lands in the implementation plan):

- **Phase A** — backend core modules: 5 × (impl + test) ≈ 10 tasks
- **Phase B** — backend integration test: 2 tasks
- **Phase C** — frontend lib modules (ajv, form-rules, problem-details, pagination, client): 5 tasks
- **Phase D** — FormRenderer + FieldRegistry + 5 field components + tests: 8 tasks
- **Phase E** — frontend integration test: 1 task
- **Phase F** — L1 audit scripts (3): 3 tasks
- **Phase G** — conventions doc updates (4): 4 tasks
- **Phase H** — full-suite smoke verification: 1 task

## 10. Invariants for downstream agents

If you (an AI or human) are building a business module in Plan 3+, the following are **hard rules** coming out of Plan 2. Each is backed by an audit or convention-auditor check.

1. Every request/response Pydantic model inherits `BaseSchema`. No exceptions.
2. Error responses are raised as `ProblemDetails`. Never `HTTPException`. Never a dict.
3. List endpoints return `Page[T]` and use `paginate()`. Never `list[T]`. Never `.all()`.
4. Cross-field validation uses the registry (`__rules__ = [must_match(a=..., b=...)]`). Never a free-form `@model_validator`.
5. Delete/transition guards live on the model (`__guards__`). Never ad-hoc `if exists(...)` checks in endpoints.
6. Forms are rendered via `<FormRenderer schema={...} />`. Never hand-rolled `<input>` trees.
7. API calls go through `api/client.ts`. Never `fetch()`, never a second Axios instance.
8. Access tokens live in `sessionStorage` or HttpOnly cookies. Never `localStorage`.
9. Ajv is the only validator. Never Zod, never Yup.
10. A rule or guard that doesn't exist in the registry cannot be used. Add it to the registry first (both sides, one PR), then use it.

Violation of any of the above is not a code-review nitpick — it's a bug that should fail the audit suite before the PR opens.

## 11. Open questions / known risks

1. **Metaclass vs `__init_subclass__` for `__rules__` consumption** — both work; `__init_subclass__` is simpler and avoids metaclass conflicts. Decision punted to implementation. If neither proves clean, fall back to a `@with_rules` decorator applied to the class.
2. **Ajv `strict: false` vs `strictSchema: false`** — we need the latter only. `strict: false` disables too many checks. Validated in implementation.
3. **How does `FormRenderer` surface server-side errors with nested paths (`addresses.0.zip`)?** — RHF supports dotted-path `setError`. Integration test must cover a nested case before we call it done.
4. **`PageQuery.sort` parser** — must be shared. Plan 2 ships a simple parser on the backend; frontend sends the raw string. No frontend parser in Plan 2.

## 12. Non-goals (explicit)

- Caching (no HTTP cache, no client cache)
- WebSocket / SSE
- File upload (Plan 5)
- Workflow DSL (Plan 6)
- OpenAPI type generation for frontend (belongs to CI, tracked separately)
- Internationalization of error messages

---

**End of design spec.** Proceed to writing-plans once approved.
