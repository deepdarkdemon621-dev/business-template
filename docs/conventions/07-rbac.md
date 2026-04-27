# 07 · RBAC (Role + Permission + Scope)

## Tables

```
departments        (id, name, parent_id, path)     -- materialized path
permissions        (id, code, description)          -- code = "resource:action"
roles              (id, code, name, is_system)
role_permissions   (role_id, permission_id, scope)  -- scope ∈ {global, dept_tree, dept, own}
user_roles         (user_id, role_id)               -- many-to-many
users              (id, email, department_id, is_superadmin)
```

## Permission code format

`resource:action`, lowercase, hyphen-separated resource names.

**Allowed actions (fixed vocabulary):**
`create`, `read`, `update`, `delete`, `list`, `export`, `approve`, `reject`, `publish`, `invoke`, `assign`, `move`

Examples: `user:create`, `department:delete`, `form-template:publish`, `ai-analysis:invoke`, `role:assign`, `department:move`.

`assign` covers granting/revoking a linkage (e.g. assigning a role to a user, attaching a department). It is distinct from `update` (which modifies the target entity itself) because grant/revoke operates on the join row, not the target.

`move` covers hierarchical re-parenting of tree-structured resources (e.g. moving a department subtree under a new parent). It is distinct from `update` because it rewrites the parent edge + materialized-path for every descendant, not just the target row's own fields.

Extending the action vocabulary requires a PR review. Don't invent `yeet` or `nuke`.

### Scope of this vocabulary

The fixed action list above governs **permission codes** only (the `action` segment of `permissions.code`). It does NOT govern `audit_events.action`, which is an audit-domain field with its own broader vocabulary (`login`, `logout`, `password_changed`, `session_revoked`, `login_failed`, `password_reset_requested`, `password_reset_consumed`, `pruned`, plus the standard CRUD verbs). Audit verbs describe what happened in the world; permission actions are the gate that authorized it. Conflating them would force every auditable verb to first become a permission code, which is wrong: `auth.login` is not gated by `auth:login` — it's gated by being able to authenticate at all.

## Scope semantics

| Scope | Row visibility |
|---|---|
| `global` | All rows in the system |
| `dept_tree` | Actor's department + all descendants (materialized path `LIKE '<actor_dept_path>%'`) |
| `dept` | Actor's department only |
| `own` | Rows where `created_by == actor.id` |

`is_superadmin=True` bypasses all permission checks. Only the built-in superadmin role grants this. No self-service way to set it.

## Declarative checks (endpoints)

```python
@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_perm("user:delete"))],
)
async def delete_user(
    user_id: UUID,
    target: User = Depends(load_in_scope("user:delete", get_user)),
    service: UserService = Depends(),
):
    await service.delete(target)
```

- `require_perm` → 403 if user lacks the permission in any scope
- `load_in_scope` → 404 if the target isn't visible in the user's scope for this permission

## Declarative checks (list queries)

```python
stmt = apply_scope(select(User), current_user, "user:list", dept_field="department_id")
```

Never write `select(User).where(...)` directly on a protected resource without `apply_scope`. The audit scanner flags this.

## Seed

- `app/core/permissions.py` defines permission codes as constants. At app startup, the list is **upserted** into the DB: new codes inserted, removed codes logged as `WARN` (not deleted, to preserve role_permissions history)
- Built-in roles (`superadmin`, `admin`, `member`) seeded via Alembic data migration

## FE surface

- `GET /me/permissions` returns `[{ code, scope }]`
- `usePermissions().can("user:delete")` → boolean (UI only; BE is source of truth)
- FE rendering: hide/disable buttons based on permissions; NEVER block BE work on this

## Mechanical enforcement

- `scripts/audit/audit_permissions.py` — AST-scan every FastAPI route for `require_perm` or `public=True`
- `scripts/audit/audit_scope.py` (Plan 2) — grep `select(` on models declared as "scoped" (metadata) without `apply_scope`
- CI test: every permission code referenced in code must exist in `app/core/permissions.py`
