# 10. Form consistency (5-layer rule)

Every form field must have all five layers aligned. Treat any drift as a real bug, same severity as a crash.

1. **FE required-marker** — visible red asterisk `*` on every required field's label.
2. **FE validation** — ajv via `FormRenderer`; field-level via `required` / `pattern` / format; cross-field via `x-rules`.
3. **Error messages** — on-blur / on-submit, the offending field lights up with a field-specific message (red border + red text under the field), not a generic form error.
4. **BE validation** — Pydantic schema matches FE constraints. Cross-field via `x-rules` registry. Error shape `{"loc": ["body", "<field>"], "msg": ...}`.
5. **DB constraint** — `NOT NULL`, `CHECK`, `UNIQUE`, length match Pydantic constraints exactly.

Enforcement:
- `audit_schema_db_consistency.py` catches Pydantic vs migration drift at L1.
- `convention-auditor` walks all 5 layers per field before any feature ships.

When a form is deferred to a later plan, record layer gaps in `docs/backlog.md` so they are not forgotten.
