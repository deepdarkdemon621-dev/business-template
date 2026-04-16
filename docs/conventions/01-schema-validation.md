# 01 · Schema / Validation Contract

## Rule

> **Pydantic is the only authoring format for validation.**
> **JSON Schema is the transport format between BE and FE.**
> **Nobody hand-writes JSON Schema files.**

## Why

A single source of truth eliminates FE/BE validation drift. Pydantic gives Python type safety, IDE completion, and refactor safety. JSON Schema gives FE a runtime-loadable schema for both static and dynamic (future form engine) forms.

## How

### Static forms (developers write Pydantic)

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Literal

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(max_length=120)
    role: Literal["admin", "member"]
    age: int = Field(ge=18, le=120)
    phone: str = Field(pattern=r"^\+?[0-9\s\-()]{7,20}$")
```

FastAPI auto-exports this to OpenAPI/JSON Schema. FE consumes via `openapi-typescript` (→ TS types) and via ajv (→ runtime validation in forms).

### Dynamic forms (V2 form engine)

Admin UI writes config → `form_engine.compile(config)` → JSON Schema → same FE renderer, same ajv instance. Backend uses `pydantic.create_model(..., **fields)` to dynamically construct a Pydantic class for validation.

## Cross-field rules: FormRuleRegistry

Pydantic's `@model_validator` does not auto-export to JSON Schema. For cross-field rules we use a **shared rule vocabulary** implemented on both sides:

| Rule | Arguments | Meaning |
|---|---|---|
| `dateOrder` | `{ start, end }` | `end >= start` |
| `mustMatch` | `{ a, b }` | `a == b` (password confirm, etc.) |
| `conditionalRequired` | `{ when: {field, equals}, then: [fields] }` | If `when` condition true, `then` fields required |
| `mutuallyExclusive` | `{ fields: [...] }` | At most one filled |
| `uniqueInList` | `{ path, key }` | List at `path`, each item's `key` unique |

Attach via `json_schema_extra`:

```python
class ApplicationCreate(BaseModel):
    start_date: date
    end_date: date
    model_config = {
        "json_schema_extra": {
            "x-rules": [
                {"type": "dateOrder", "start": "start_date", "end": "end_date"}
            ]
        }
    }
```

The same declaration drives an auto-generated `@model_validator` on the BE side (from the registry) AND is consumed by ajv on the FE.

## Boundaries

**Allowed:** any rule present in FormRuleRegistry.
**Not allowed:** free-form Python lambdas / inline `@model_validator` for cross-field logic when an equivalent vocabulary rule would fit.
**Escape hatch:** if the rule truly can't be expressed in the vocabulary, add a new entry to the registry with both BE + FE implementations before using it. Document the addition in a PR.

## Mechanical enforcement

- `scripts/audit/audit_json_schema.sh` — fails if any `*.schema.json` appears under `backend/` or `frontend/src/` (excluding `frontend/src/api/generated/`)
- `scripts/audit/audit_listing.py` — reviews endpoint signatures for missing Pydantic response_model
- CI step: run `pytest` against `tests/contracts/` (to be added in Plan 2) that round-trips Pydantic → JSON Schema → ajv-validates known samples
