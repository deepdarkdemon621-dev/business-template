# 02 · Service Guards (Business Invariants)

## Rule

> **All pre-mutation business invariants live in a guard registry, not inline in endpoints.**

## Why

Without a vocabulary, every developer (and AI) writes ad-hoc `if exists(...): raise` checks. Same invariant gets re-invented in slightly different ways; rules drift; error codes differ; FE can't render consistent messages.

## Vocabulary (ServiceGuardRegistry)

| Guard | Arguments | Meaning |
|---|---|---|
| `NoDependents` | `(table, fk_col)` | Forbid delete if rows exist in `table` where `fk_col == self.id` |
| `NoActiveChildren` | `(relation)` | Forbid op if any related row has `is_active=True` |
| `StateAllows` | `(field, allowed=[...])` | Forbid op unless `self.<field>` in `allowed` |
| `ImmutableAfter` | `(field, frozen_from=...)` | Forbid update when `self.<field>` has reached the frozen state |
| `SameDepartment` | — | Target must share `department_id` with actor |

## Declarative usage

```python
class Department(Base):
    __guards__ = {
        "delete": [
            NoDependents("users", "department_id"),
            NoDependents("roles", "default_department_id"),
        ],
    }
```

Service base class (Plan 2) runs `__guards__` for the matching operation before executing the mutation. On failure, raises `GuardViolationError(code="no_dependents", ctx={"table": "users", "count": 12})`.

## FE deletability query

Every guarded resource exposes `GET /{resource}/{id}/deletable`:

```json
{
  "can": false,
  "reason_code": "no_dependents",
  "details": { "table": "users", "count": 12 }
}
```

FE uses this to disable destructive buttons with an explanatory tooltip, not let the user click and get a 409.

## Defense in depth

- DB FK constraints use `ON DELETE RESTRICT` — ultimate backstop
- Service-layer guards — primary UX layer
- FE `deletable?` query — best UX

## Boundaries

**Allowed:** guards in registry, `__guards__` declaration on models.
**Not allowed:** `if <check>: raise HTTPException(...)` inside endpoints for pre-mutation business checks.
**Escape hatch:** add new guard type to registry with tests. Don't add it inline.

## Mechanical enforcement

- `scripts/audit/audit_guards.py` (added in Plan 2) — AST scan: every model with `delete` route must have `__guards__` declared OR be explicitly tagged `__no_guards__ = True` with a comment justification
- CI test: every `GuardViolationError.code` must appear in the registry keys set

## Concrete guards (shipped in Plan 2)

### Declarative attachment

```python
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
