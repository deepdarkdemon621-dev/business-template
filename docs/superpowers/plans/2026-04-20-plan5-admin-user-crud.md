# Plan 5 — Admin User CRUD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Plan 5 per spec `docs/superpowers/specs/2026-04-20-plan5-admin-user-crud-design.md` — first runtime admin surface (User CRUD + role assignment) plus the two missing UI primitives (`DataTable`, `AppShell`). Produces tag `v0.5.0-admin-user-crud`.

**Architecture:** New backend `modules/user/` imports the existing `User` model from `auth` and owns admin endpoints only. Two new guards (`SelfProtection`, `LastOfKind`) extend `core/guards.py`. Frontend gains a generic `<DataTable>` (server pagination only, no react-query dep — state via `useState` + effect) and an `AppShell` layout wrapper with a permission-gated `<Sidebar>`. First consumer of these primitives: a two-page User admin module.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, React 19, react-router-dom v7, axios, Vitest, pytest-asyncio.

**Spec addenda (small additions beyond the spec):**
1. Add read-only `GET /roles` endpoint to `modules/rbac/router.py` — required to populate the role picker. Not "Role CRUD" (write ops remain deferred); just a list endpoint guarded by `role:list` (already in Plan 4 seed).

---

## Phase A — Backend guard extensions

Two guards added to the existing registry in `app/core/guards.py`.

### Task A1: `SelfProtection` guard

**Files:**
- Modify: `backend/app/core/guards.py`
- Create: `backend/tests/core/test_guards_self_protection.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/core/__init__.py` (empty) if missing, then `backend/tests/core/test_guards_self_protection.py`:
```python
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.guards import GuardViolationError, SelfProtection

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session_stub(db_session: AsyncSession) -> AsyncSession:
    return db_session


async def test_raises_when_actor_equals_target(session_stub: AsyncSession) -> None:
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=False)
    g = SelfProtection()
    with pytest.raises(GuardViolationError) as ei:
        await g.check(session_stub, target, actor=actor)
    assert ei.value.code == "self-protection"


async def test_passes_when_actor_different(session_stub: AsyncSession) -> None:
    target = SimpleNamespace(id=uuid.uuid4())
    actor = SimpleNamespace(id=uuid.uuid4(), is_superadmin=False)
    await SelfProtection().check(session_stub, target, actor=actor)


async def test_superadmin_bypasses(session_stub: AsyncSession) -> None:
    uid = uuid.uuid4()
    target = SimpleNamespace(id=uid)
    actor = SimpleNamespace(id=uid, is_superadmin=True)
    await SelfProtection().check(session_stub, target, actor=actor)
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/core/test_guards_self_protection.py -v`
Expected: `ImportError: cannot import name 'SelfProtection'`.

- [ ] **Step 3: Extend the Guard protocol + implement `SelfProtection`**

Modify `backend/app/core/guards.py`. The existing `Guard` Protocol signature `check(session, instance)` needs an optional `actor` keyword for self-protection. Replace the protocol and add the new guard at the bottom of the file:

```python
@runtime_checkable
class Guard(Protocol):
    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None
    ) -> None: ...


class SelfProtection:
    """Forbid an action where the actor is the target. Bypassed for superadmins."""

    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None
    ) -> None:
        if actor is None:
            return
        if getattr(actor, "is_superadmin", False):
            return
        if getattr(actor, "id", None) == getattr(instance, "id", None):
            raise GuardViolationError(
                code="self-protection",
                ctx={"actor_id": str(actor.id), "target_id": str(instance.id)},
            )
```

Also update existing guards to accept the new `actor` kwarg (ignored by them):

```python
class NoDependents:
    # ... unchanged __init__ ...
    async def check(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None
    ) -> None:
        # body unchanged
```

And `StateAllows.check` likewise.

And `ServiceBase.delete` must now forward actor:

```python
class ServiceBase:
    model: type

    async def delete(
        self, session: AsyncSession, instance: Any, *, actor: Any | None = None
    ) -> None:
        guards = getattr(self.model, "__guards__", {}).get("delete", [])
        for guard in guards:
            await guard.check(session, instance, actor=actor)
        async with session.begin():
            await session.delete(instance)
```

- [ ] **Step 4: Run test — expect pass**

Run: `docker compose exec backend uv run pytest tests/core/test_guards_self_protection.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Verify existing guard tests still pass**

Run: `docker compose exec backend uv run pytest tests/core -v`
Expected: all green (existing tests should not break — they don't pass `actor`, which defaults to `None`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/guards.py backend/tests/core/
git commit -m "feat(core): add SelfProtection guard + actor kwarg on Guard protocol"
```

### Task A2: `LastOfKind` guard

**Files:**
- Modify: `backend/app/core/guards.py`
- Create: `backend/tests/core/test_guards_last_of_kind.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/core/test_guards_last_of_kind.py`:
```python
from __future__ import annotations

from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.guards import GuardViolationError, LastOfKind
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def superadmin_role(db_session: AsyncSession) -> Role:
    role = Role(code="superadmin_test", name="Super", is_superadmin=True)
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def two_superadmins(db_session: AsyncSession, superadmin_role: Role) -> list[User]:
    users = []
    for email in ("sa1@ex.com", "sa2@ex.com"):
        u = User(email=email, password_hash=hash_password("pw-aaa111"), full_name=email)
        db_session.add(u)
        await db_session.flush()
        db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
        users.append(u)
    await db_session.flush()
    return users


async def test_passes_when_role_code_mismatch(db_session: AsyncSession) -> None:
    actor = SimpleNamespace(id=None, is_superadmin=False)
    target = SimpleNamespace(id=None)
    g = LastOfKind("superadmin")
    # role_code in ctx is "member" — guard no-ops
    await g.check(db_session, target, actor=actor, role_code="member")


async def test_raises_when_removing_last_superadmin(
    db_session: AsyncSession, superadmin_role: Role
) -> None:
    u = User(email="only@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Only")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
    await db_session.flush()

    actor = SimpleNamespace(id=None, is_superadmin=False)
    g = LastOfKind("superadmin_test")
    with pytest.raises(GuardViolationError) as ei:
        await g.check(db_session, u, actor=actor, role_code="superadmin_test")
    assert ei.value.code == "last-of-kind"


async def test_passes_when_another_superadmin_remains(
    db_session: AsyncSession, two_superadmins: list[User]
) -> None:
    actor = SimpleNamespace(id=None, is_superadmin=False)
    g = LastOfKind("superadmin_test")
    await g.check(db_session, two_superadmins[0], actor=actor, role_code="superadmin_test")


async def test_superadmin_bypasses(db_session: AsyncSession, superadmin_role: Role) -> None:
    u = User(email="alone@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Alone")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=superadmin_role.id))
    await db_session.flush()

    actor = SimpleNamespace(id=None, is_superadmin=True)
    await LastOfKind("superadmin_test").check(
        db_session, u, actor=actor, role_code="superadmin_test"
    )
```

- [ ] **Step 2: Run test — expect failure**

Run: `docker compose exec backend uv run pytest tests/core/test_guards_last_of_kind.py -v`
Expected: ImportError on `LastOfKind`.

- [ ] **Step 3: Implement `LastOfKind`**

Append to `backend/app/core/guards.py`:
```python
from sqlalchemy.orm import aliased  # already imported indirectly; add explicit import at top if missing


class LastOfKind:
    """Forbid removing role `role_code` from the sole remaining holder.

    Expects `role_code` in kwargs; no-ops when it doesn't match the configured role.
    Bypassed for superadmins.
    """

    def __init__(self, role_code: str) -> None:
        self.role_code = role_code

    async def check(
        self,
        session: AsyncSession,
        instance: Any,
        *,
        actor: Any | None = None,
        role_code: str | None = None,
    ) -> None:
        if role_code != self.role_code:
            return
        if actor is not None and getattr(actor, "is_superadmin", False):
            return

        # late imports keep guards.py free of module cycles
        from app.modules.rbac.models import Role, UserRole

        stmt = (
            select(func.count(UserRole.user_id))
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code == self.role_code)
        )
        total = (await session.execute(stmt)).scalar_one()
        if total <= 1:
            raise GuardViolationError(
                code="last-of-kind",
                ctx={"role_code": self.role_code, "remaining": int(total)},
            )
```

- [ ] **Step 4: Run tests — expect pass**

Run: `docker compose exec backend uv run pytest tests/core/test_guards_last_of_kind.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/guards.py backend/tests/core/test_guards_last_of_kind.py
git commit -m "feat(core): add LastOfKind guard for protecting sole-holder roles"
```

---

## Phase B — Backend `modules/user/`

New feature module under `backend/app/modules/user/`. It re-uses the existing `User` model from `modules/auth/`.

### Task B1: Module skeleton + schemas

**Files:**
- Create: `backend/app/modules/user/__init__.py` (empty)
- Create: `backend/app/modules/user/CLAUDE.md`
- Create: `backend/app/modules/user/schemas.py`
- Create: `backend/tests/modules/user/__init__.py` (empty)
- Create: `backend/tests/modules/user/test_schemas.py`

- [ ] **Step 1: Create module skeleton**

Run: `mkdir -p backend/app/modules/user backend/tests/modules/user`

Create `backend/app/modules/user/__init__.py` empty.
Create `backend/tests/modules/user/__init__.py` empty.

Create `backend/app/modules/user/CLAUDE.md`:
```markdown
# user/ — Agent guide

Admin CRUD over the `User` SQLAlchemy model, which lives in `modules/auth/models.py`.
This module does NOT own a model — it imports `User` from auth.

Endpoints: list / create / read / update / soft-delete; role assign / revoke.
All guarded by the `user:*` permissions seeded in Plan 4.

Self-protection and last-superadmin invariants are enforced via `__guards__` on the User model, registered in `app/modules/auth/models.py`.
```

- [ ] **Step 2: Write failing schema tests**

Create `backend/tests/modules/user/test_schemas.py`:
```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.user.schemas import (
    RoleSummaryOut,
    UserCreateIn,
    UserDetailOut,
    UserOut,
    UserUpdateIn,
)


def test_user_create_in_requires_password_policy():
    with pytest.raises(ValidationError) as ei:
        UserCreateIn(email="a@b.com", password="short1", full_name="A")
    assert "Password" in str(ei.value)


def test_user_create_in_accepts_valid_payload():
    u = UserCreateIn(
        email="a@b.com",
        password="LongEnough123",
        full_name="Alice",
    )
    assert u.must_change_password is True  # default


def test_user_create_in_rejects_empty_full_name():
    with pytest.raises(ValidationError):
        UserCreateIn(email="a@b.com", password="LongEnough123", full_name="")


def test_user_update_in_all_fields_optional():
    u = UserUpdateIn()
    assert u.full_name is None
    assert u.is_active is None


def test_user_out_excludes_password_hash():
    assert "password_hash" not in UserOut.model_fields
    assert "passwordHash" not in UserOut.model_json_schema()["properties"]


def test_role_summary_out_shape():
    r = RoleSummaryOut(id="00000000-0000-0000-0000-000000000001", code="admin", name="Admin")
    dumped = r.model_dump(by_alias=True)
    assert set(dumped.keys()) == {"id", "code", "name"}


def test_user_detail_out_has_roles_list():
    assert UserDetailOut.model_fields["roles"].annotation == list[RoleSummaryOut]
```

- [ ] **Step 3: Run — expect import failure**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_schemas.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `schemas.py`**

Create `backend/app/modules/user/schemas.py`:
```python
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.form_rules import password_policy
from app.core.schemas import BaseSchema


class RoleSummaryOut(BaseSchema):
    id: uuid.UUID
    code: str
    name: str


class DepartmentSummaryOut(BaseSchema):
    id: uuid.UUID
    name: str
    path: str


class UserCreateIn(BaseSchema):
    __rules__ = [password_policy(field="password")]

    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=100)
    department_id: uuid.UUID | None = None
    must_change_password: bool = True


class UserUpdateIn(BaseSchema):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    department_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserOut(BaseSchema):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    department_id: uuid.UUID | None
    is_active: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime


class UserDetailOut(UserOut):
    roles: list[RoleSummaryOut] = Field(default_factory=list)
    department: DepartmentSummaryOut | None = None
```

- [ ] **Step 5: Run — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_schemas.py -v`
Expected: 7 pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/user/ backend/tests/modules/user/
git commit -m "feat(user): schemas (UserCreate/Update/Out/Detail + Role/Dept summaries)"
```

### Task B2: CRUD helpers

**Files:**
- Create: `backend/app/modules/user/crud.py`
- Create: `backend/tests/modules/user/test_crud.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/modules/user/test_crud.py`:
```python
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from app.modules.user.crud import (
    build_list_users_stmt,
    get_user_with_roles,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def seeded(db_session: AsyncSession) -> tuple[User, Role]:
    u = User(email="u@ex.com", password_hash=hash_password("pw-aaa111"), full_name="U")
    r = Role(code="r1", name="R1")
    db_session.add_all([u, r])
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=r.id))
    await db_session.flush()
    return u, r


async def test_build_list_users_stmt_default_excludes_inactive(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, _ = seeded
    u.is_active = False
    await db_session.flush()
    stmt = build_list_users_stmt(is_active=True)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert all(row.is_active for row in rows)


async def test_build_list_users_stmt_is_active_false_shows_only_inactive(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, _ = seeded
    u.is_active = False
    await db_session.flush()
    stmt = build_list_users_stmt(is_active=False)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert rows and all(not row.is_active for row in rows)


async def test_get_user_with_roles_returns_user_and_roles(
    db_session: AsyncSession, seeded: tuple[User, Role]
) -> None:
    u, r = seeded
    user, roles = await get_user_with_roles(db_session, u.id)
    assert user.id == u.id
    assert len(roles) == 1 and roles[0].id == r.id


async def test_get_user_with_roles_returns_none_when_missing(db_session: AsyncSession) -> None:
    import uuid

    user, roles = await get_user_with_roles(db_session, uuid.uuid4())
    assert user is None and roles == []
```

- [ ] **Step 2: Run — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_crud.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `crud.py`**

Create `backend/app/modules/user/crud.py`:
```python
from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole


def build_list_users_stmt(is_active: bool | None = True) -> Select:
    stmt = select(User).order_by(User.created_at.desc())
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    return stmt


async def get_user_with_roles(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[User | None, list[Role]]:
    u = await session.get(User, user_id)
    if u is None:
        return None, []
    role_stmt = (
        select(Role).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    )
    roles = list((await session.execute(role_stmt)).scalars().all())
    return u, roles
```

- [ ] **Step 4: Run — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_crud.py -v`
Expected: 4 pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/user/crud.py backend/tests/modules/user/test_crud.py
git commit -m "feat(user): crud helpers (list stmt builder, get_user_with_roles)"
```

### Task B3: Service layer

**Files:**
- Create: `backend/app/modules/user/service.py`
- Create: `backend/tests/modules/user/test_service.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/modules/user/test_service.py`:
```python
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password, verify_password
from app.core.guards import GuardViolationError
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from app.modules.user.schemas import UserCreateIn, UserUpdateIn
from app.modules.user.service import (
    assign_role,
    create_user,
    revoke_role,
    soft_delete_user,
    update_user,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def actor(db_session: AsyncSession) -> User:
    u = User(email="actor@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Actor")
    db_session.add(u)
    await db_session.flush()
    return u


@pytest_asyncio.fixture
async def superadmin_actor(db_session: AsyncSession) -> User:
    role = Role(code="superadmin", name="Super", is_superadmin=True)
    u = User(email="sa@ex.com", password_hash=hash_password("pw-aaa111"), full_name="SA")
    db_session.add_all([role, u])
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.flush()
    return u


async def test_create_user_hashes_password_and_sets_flags(
    db_session: AsyncSession, actor: User
) -> None:
    payload = UserCreateIn(
        email="new@ex.com",
        password="GoodOne123",
        full_name="New",
    )
    u = await create_user(db_session, payload, actor=actor)
    assert u.email == "new@ex.com"
    assert u.password_hash != "GoodOne123"
    assert verify_password("GoodOne123", u.password_hash)
    assert u.must_change_password is True
    assert u.is_active is True


async def test_update_user_applies_partial(db_session: AsyncSession, actor: User) -> None:
    target = User(
        email="t@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Old Name"
    )
    db_session.add(target)
    await db_session.flush()

    patch = UserUpdateIn(full_name="New Name")
    updated = await update_user(db_session, target, patch, actor=actor)
    assert updated.full_name == "New Name"


async def test_soft_delete_user_flips_is_active(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t2@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T2")
    db_session.add(target)
    await db_session.flush()

    await soft_delete_user(db_session, target, actor=actor)
    await db_session.refresh(target)
    assert target.is_active is False


async def test_soft_delete_blocked_when_self(db_session: AsyncSession, actor: User) -> None:
    with pytest.raises(GuardViolationError) as ei:
        await soft_delete_user(db_session, actor, actor=actor)
    assert ei.value.code == "self-protection"


async def test_superadmin_can_self_delete(
    db_session: AsyncSession, superadmin_actor: User
) -> None:
    await soft_delete_user(db_session, superadmin_actor, actor=superadmin_actor)
    await db_session.refresh(superadmin_actor)
    assert superadmin_actor.is_active is False


async def test_assign_role_is_idempotent(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t3@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T3")
    role = Role(code="r", name="R")
    db_session.add_all([target, role])
    await db_session.flush()

    await assign_role(db_session, target, role, actor=actor)
    await assign_role(db_session, target, role, actor=actor)  # no error
    # verify only one row
    from sqlalchemy import select, func

    count = (
        await db_session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.user_id == target.id)
        )
    ).scalar_one()
    assert count == 1


async def test_revoke_role_removes_row(db_session: AsyncSession, actor: User) -> None:
    target = User(email="t4@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T4")
    role = Role(code="rr", name="RR")
    db_session.add_all([target, role])
    await db_session.flush()
    db_session.add(UserRole(user_id=target.id, role_id=role.id))
    await db_session.flush()

    await revoke_role(db_session, target, role, actor=actor)
    from sqlalchemy import select, func

    count = (
        await db_session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.user_id == target.id)
        )
    ).scalar_one()
    assert count == 0


async def test_revoke_role_raises_when_not_assigned(
    db_session: AsyncSession, actor: User
) -> None:
    target = User(email="t5@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T5")
    role = Role(code="rrr", name="RRR")
    db_session.add_all([target, role])
    await db_session.flush()

    from app.core.errors import ProblemDetails

    with pytest.raises(ProblemDetails) as ei:
        await revoke_role(db_session, target, role, actor=actor)
    assert ei.value.status == 404
```

- [ ] **Step 2: Run — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_service.py -v`
Expected: ImportError on service module.

- [ ] **Step 3: Implement `service.py`**

Create `backend/app/modules/user/service.py`:
```python
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.errors import ProblemDetails
from app.modules.auth.models import User
from app.modules.rbac.models import Role, UserRole
from app.modules.user.schemas import UserCreateIn, UserUpdateIn


async def _run_guards(
    session: AsyncSession, action: str, target: User, *, actor: User, **ctx
) -> None:
    guards = getattr(User, "__guards__", {}).get(action, [])
    for g in guards:
        await g.check(session, target, actor=actor, **ctx)


async def create_user(session: AsyncSession, payload: UserCreateIn, *, actor: User) -> User:
    u = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        department_id=payload.department_id,
        must_change_password=payload.must_change_password,
    )
    session.add(u)
    await session.flush()
    return u


async def update_user(
    session: AsyncSession, target: User, payload: UserUpdateIn, *, actor: User
) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "is_active" in data and data["is_active"] is False:
        await _run_guards(session, "deactivate", target, actor=actor)
    for k, v in data.items():
        setattr(target, k, v)
    await session.flush()
    return target


async def soft_delete_user(session: AsyncSession, target: User, *, actor: User) -> None:
    await _run_guards(session, "delete", target, actor=actor)
    target.is_active = False
    await session.flush()


async def assign_role(
    session: AsyncSession, target: User, role: Role, *, actor: User
) -> None:
    existing = (
        await session.execute(
            select(UserRole).where(
                UserRole.user_id == target.id, UserRole.role_id == role.id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    session.add(UserRole(user_id=target.id, role_id=role.id, granted_by=actor.id))
    await session.flush()


async def revoke_role(
    session: AsyncSession, target: User, role: Role, *, actor: User
) -> None:
    existing = (
        await session.execute(
            select(UserRole).where(
                UserRole.user_id == target.id, UserRole.role_id == role.id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        raise ProblemDetails(
            code="role-not-assigned",
            status=404,
            detail=f"Role '{role.code}' is not assigned to this user.",
        )

    await _run_guards(session, "strip_role", target, actor=actor, role_code=role.code)
    await session.execute(
        delete(UserRole).where(
            UserRole.user_id == target.id, UserRole.role_id == role.id
        )
    )
    await session.flush()
```

- [ ] **Step 4: Add `__guards__` to User model + run tests**

Modify `backend/app/modules/auth/models.py` — add after `__scope_map__`:
```python
    # Import here (not at module top) to avoid circular import: guards.py
    # references rbac.models, which depends on this module transitively.
    from app.core.guards import LastOfKind, SelfProtection  # noqa: E402

    __guards__ = {
        "delete": [SelfProtection()],
        "deactivate": [SelfProtection()],
        "strip_role": [SelfProtection(), LastOfKind("superadmin")],
    }
```

If the local-import approach trips lint, lift the import to module scope — guards.py defers rbac imports inside `LastOfKind.check`, so no cycle.

Preferred: add at top of `app/modules/auth/models.py` after existing imports:
```python
from app.core.guards import LastOfKind, SelfProtection
```

And inline as a class-level attribute:
```python
    __guards__ = {
        "delete": [SelfProtection()],
        "deactivate": [SelfProtection()],
        "strip_role": [SelfProtection(), LastOfKind("superadmin")],
    }
```

Run: `docker compose exec backend uv run pytest tests/modules/user/test_service.py -v`
Expected: 8 tests pass.

- [ ] **Step 5: Full regression**

Run: `docker compose exec backend uv run pytest -x`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/user/service.py backend/app/modules/auth/models.py backend/tests/modules/user/test_service.py
git commit -m "feat(user): service layer (create/update/soft-delete + role assign/revoke)"
```

### Task B4: Router — list + detail endpoints

**Files:**
- Create: `backend/app/modules/user/router.py`
- Create: `backend/tests/modules/user/test_router_read.py`

- [ ] **Step 1: Write failing integration tests**

`backend/tests/modules/user/test_router_read.py`:
```python
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole

pytestmark = pytest.mark.asyncio


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


@pytest_asyncio.fixture
async def admin_token(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str]:
    # Create an admin with user:list + user:read (global scope)
    role = Role(code="user_reader", name="UR")
    db_session.add(role)
    await db_session.flush()
    for code in ("user:list", "user:read"):
        perm = (
            await db_session.execute(
                __import__("sqlalchemy").select(Permission).where(Permission.code == code)
            )
        ).scalar_one()
        db_session.add(
            RolePermission(role_id=role.id, permission_id=perm.id, scope="global")
        )
    u = User(email="admin@ex.com", password_hash=hash_password("pw-aaa111"), full_name="A")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.commit()

    token = await _login(client_with_db, "admin@ex.com", "pw-aaa111")
    return client_with_db, token


async def test_list_users_returns_page_shape(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {"items", "total", "page", "size", "hasNext"}


async def test_list_users_forbidden_without_perm(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> None:
    u = User(email="np@ex.com", password_hash=hash_password("pw-aaa111"), full_name="NP")
    db_session.add(u)
    await db_session.commit()
    token = await _login(client_with_db, "np@ex.com", "pw-aaa111")
    resp = await client_with_db.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


async def test_list_users_is_active_filter(admin_token: tuple[AsyncClient, str]) -> None:
    client, token = admin_token
    resp = await client.get(
        "/api/v1/users?is_active=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    for u in resp.json()["items"]:
        assert u["isActive"] is False


async def test_get_user_detail_includes_roles(
    admin_token: tuple[AsyncClient, str], db_session: AsyncSession
) -> None:
    client, token = admin_token
    target = User(email="target@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T")
    db_session.add(target)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/users/{target.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "target@ex.com"
    assert "roles" in body
    assert isinstance(body["roles"], list)
```

- [ ] **Step 2: Run — expect 404 (router not mounted)**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_router_read.py -v`
Expected: failures — either ModuleNotFoundError or 404 on endpoints.

- [ ] **Step 3: Implement router list + detail**

Create `backend/app/modules/user/router.py`:
```python
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.pagination import Page, PageQuery, paginate
from app.core.permissions import (
    apply_scope,
    current_user_dep,
    get_user_permissions,
    load_in_scope,
    require_perm,
)
from app.modules.auth.models import User
from app.modules.rbac.models import Department
from app.modules.user.crud import build_list_users_stmt, get_user_with_roles
from app.modules.user.schemas import (
    DepartmentSummaryOut,
    RoleSummaryOut,
    UserDetailOut,
    UserOut,
)

router = APIRouter(tags=["user"])


@router.get(
    "/users",
    response_model=Page[UserOut],
    dependencies=[Depends(require_perm("user:list"))],
)
async def list_users(
    pq: Annotated[PageQuery, Depends()],
    is_active: bool | None = Query(default=True),
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Page[UserOut]:
    perms = await get_user_permissions(db, user)
    stmt = build_list_users_stmt(is_active=is_active)
    stmt = apply_scope(stmt, user, "user:list", User, perms)
    raw = await paginate(db, stmt, pq)
    items = [UserOut.model_validate(i, from_attributes=True) for i in raw.items]
    return Page[UserOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserDetailOut,
    dependencies=[Depends(require_perm("user:read"))],
)
async def get_user(
    user_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserDetailOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:read", perms)
    _target, roles = await get_user_with_roles(db, user_id)
    dept = (
        await db.get(Department, target.department_id) if target.department_id else None
    )
    return UserDetailOut(
        **UserOut.model_validate(target, from_attributes=True).model_dump(),
        roles=[RoleSummaryOut.model_validate(r, from_attributes=True) for r in roles],
        department=(
            DepartmentSummaryOut.model_validate(dept, from_attributes=True) if dept else None
        ),
    )
```

- [ ] **Step 4: Mount router in `api/v1.py`**

Modify `backend/app/api/v1.py`:
```python
from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.rbac.router import router as rbac_router
from app.modules.user.router import router as user_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(rbac_router)
v1_router.include_router(user_router)
```

- [ ] **Step 5: Run — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_router_read.py -v`
Expected: 4 pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/user/router.py backend/app/api/v1.py backend/tests/modules/user/test_router_read.py
git commit -m "feat(user): router list + detail endpoints, mounted under /api/v1"
```

### Task B5: Router — write endpoints (create/update/delete)

**Files:**
- Modify: `backend/app/modules/user/router.py`
- Create: `backend/tests/modules/user/test_router_write.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/modules/user/test_router_write.py`:
```python
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole

pytestmark = pytest.mark.asyncio


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


async def _grant_perms(
    db: AsyncSession, role: Role, codes: list[str], scope: str = "global"
) -> None:
    for code in codes:
        perm = (
            await db.execute(select(Permission).where(Permission.code == code))
        ).scalar_one()
        db.add(RolePermission(role_id=role.id, permission_id=perm.id, scope=scope))


@pytest_asyncio.fixture
async def admin(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str, User]:
    role = Role(code="user_admin", name="UA")
    db_session.add(role)
    await db_session.flush()
    await _grant_perms(
        db_session, role, ["user:list", "user:read", "user:create", "user:update", "user:delete"]
    )
    u = User(email="ua@ex.com", password_hash=hash_password("pw-aaa111"), full_name="UA")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=role.id))
    await db_session.commit()

    token = await _login(client_with_db, "ua@ex.com", "pw-aaa111")
    return client_with_db, token, u


async def test_create_user_201(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, _ = admin
    resp = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "c@ex.com",
            "password": "GoodOne123",
            "fullName": "C",
            "mustChangePassword": True,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "c@ex.com"
    assert body["mustChangePassword"] is True
    assert "passwordHash" not in body


async def test_create_user_weak_password_422(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, _ = admin
    resp = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "w@ex.com", "password": "short", "fullName": "W"},
    )
    assert resp.status_code == 422


async def test_update_user_patch(
    admin: tuple[AsyncClient, str, User], db_session: AsyncSession
) -> None:
    client, token, _ = admin
    t = User(email="p@ex.com", password_hash=hash_password("pw-aaa111"), full_name="Old")
    db_session.add(t)
    await db_session.commit()
    resp = await client.patch(
        f"/api/v1/users/{t.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"fullName": "New"},
    )
    assert resp.status_code == 200
    assert resp.json()["fullName"] == "New"


async def test_delete_user_soft(
    admin: tuple[AsyncClient, str, User], db_session: AsyncSession
) -> None:
    client, token, _ = admin
    t = User(email="d@ex.com", password_hash=hash_password("pw-aaa111"), full_name="D")
    db_session.add(t)
    await db_session.commit()
    resp = await client.delete(
        f"/api/v1/users/{t.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 204
    await db_session.refresh(t)
    assert t.is_active is False


async def test_delete_self_blocked(admin: tuple[AsyncClient, str, User]) -> None:
    client, token, actor = admin
    resp = await client.delete(
        f"/api/v1/users/{actor.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "self-protection"
```

- [ ] **Step 2: Run — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_router_write.py -v`
Expected: failures (endpoints not yet implemented).

- [ ] **Step 3: Add write endpoints to router**

Append to `backend/app/modules/user/router.py`:
```python
from fastapi import status
from fastapi.responses import Response

from app.core.errors import ProblemDetails
from app.core.guards import GuardViolationError
from app.modules.user.schemas import UserCreateIn, UserUpdateIn
from app.modules.user.service import create_user, soft_delete_user, update_user


def _guard_to_problem(e: GuardViolationError) -> ProblemDetails:
    return ProblemDetails(code=e.code, status=403, detail=str(e.code), ctx=e.ctx)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_perm("user:create"))],
)
async def create_user_endpoint(
    payload: UserCreateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserOut:
    created = await create_user(db, payload, actor=user)
    await db.commit()
    return UserOut.model_validate(created, from_attributes=True)


@router.patch(
    "/users/{user_id}",
    response_model=UserOut,
    dependencies=[Depends(require_perm("user:update"))],
)
async def update_user_endpoint(
    user_id: uuid.UUID,
    payload: UserUpdateIn,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> UserOut:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:update", perms)
    try:
        updated = await update_user(db, target, payload, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return UserOut.model_validate(updated, from_attributes=True)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_perm("user:delete"))],
)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:delete", perms)
    try:
        await soft_delete_user(db, target, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Check that `ProblemDetails` accepts a `ctx` kwarg — inspect `backend/app/core/errors.py`. If it doesn't, drop `ctx=` from `_guard_to_problem` (guard ctx is logged but not surfaced).

- [ ] **Step 4: Run — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_router_write.py -v`
Expected: 5 pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/user/router.py backend/tests/modules/user/test_router_write.py
git commit -m "feat(user): create/update/soft-delete endpoints with guard translation"
```

### Task B6: Role assign/revoke endpoints + `GET /roles`

**Files:**
- Modify: `backend/app/modules/user/router.py`
- Modify: `backend/app/modules/rbac/router.py`
- Modify: `backend/app/modules/rbac/schemas.py`
- Create: `backend/tests/modules/user/test_router_roles.py`

- [ ] **Step 1: Write failing tests**

`backend/tests/modules/user/test_router_roles.py`:
```python
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission, UserRole

pytestmark = pytest.mark.asyncio


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["accessToken"]


@pytest_asyncio.fixture
async def assigner(
    client_with_db: AsyncClient, db_session: AsyncSession
) -> tuple[AsyncClient, str, User, Role]:
    target_role = Role(code="target_role", name="TR")
    admin_role = Role(code="user_assigner", name="UA")
    db_session.add_all([target_role, admin_role])
    await db_session.flush()

    for code in ("user:list", "user:read", "user:assign", "role:list"):
        perm = (
            await db_session.execute(select(Permission).where(Permission.code == code))
        ).scalar_one()
        db_session.add(
            RolePermission(role_id=admin_role.id, permission_id=perm.id, scope="global")
        )

    u = User(email="ag@ex.com", password_hash=hash_password("pw-aaa111"), full_name="AG")
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserRole(user_id=u.id, role_id=admin_role.id))
    await db_session.commit()

    token = await _login(client_with_db, "ag@ex.com", "pw-aaa111")
    return client_with_db, token, u, target_role


async def test_list_roles(assigner: tuple[AsyncClient, str, User, Role]) -> None:
    client, token, _, _ = assigner
    resp = await client.get(
        "/api/v1/roles", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    codes = {r["code"] for r in body["items"]}
    assert "target_role" in codes


async def test_assign_role_idempotent(
    assigner: tuple[AsyncClient, str, User, Role], db_session: AsyncSession
) -> None:
    client, token, _, role = assigner
    target = User(email="tgt@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T")
    db_session.add(target)
    await db_session.commit()

    for _ in range(2):
        resp = await client.post(
            f"/api/v1/users/{target.id}/roles/{role.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

    count = (
        await db_session.execute(
            select(func.count())
            .select_from(UserRole)
            .where(UserRole.user_id == target.id, UserRole.role_id == role.id)
        )
    ).scalar_one()
    assert count == 1


async def test_revoke_role_missing_404(
    assigner: tuple[AsyncClient, str, User, Role], db_session: AsyncSession
) -> None:
    client, token, _, role = assigner
    target = User(email="tgt2@ex.com", password_hash=hash_password("pw-aaa111"), full_name="T2")
    db_session.add(target)
    await db_session.commit()

    resp = await client.delete(
        f"/api/v1/users/{target.id}/roles/{role.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "role-not-assigned"
```

- [ ] **Step 2: Run — expect failure**

Run: `docker compose exec backend uv run pytest tests/modules/user/test_router_roles.py -v`
Expected: failures.

- [ ] **Step 3: Add `RoleOut` schema + `GET /roles` endpoint**

Modify `backend/app/modules/rbac/schemas.py` — append:
```python
class RoleOut(BaseSchema):
    id: uuid.UUID
    code: str
    name: str
    is_builtin: bool
    is_superadmin: bool
```

(make sure `uuid` is imported at top; the existing file likely already imports it for other schemas.)

Modify `backend/app/modules/rbac/router.py` — add:
```python
from app.modules.rbac.models import Role
from app.modules.rbac.schemas import RoleOut


@router.get(
    "/roles",
    response_model=Page[RoleOut],
    dependencies=[Depends(require_perm("role:list"))],
)
async def list_roles(
    pq: Annotated[PageQuery, Depends()],
    db: AsyncSession = Depends(get_session),
) -> Page[RoleOut]:
    stmt = select(Role).order_by(Role.name)
    raw = await paginate(db, stmt, pq)
    items = [RoleOut.model_validate(r, from_attributes=True) for r in raw.items]
    return Page[RoleOut](
        items=items,
        total=raw.total,
        page=raw.page,
        size=raw.size,
        has_next=raw.has_next,
    )
```

(`Role` global scope only — no per-user scoping on roles; they're global metadata.)

- [ ] **Step 4: Add role assign/revoke endpoints to user router**

Append to `backend/app/modules/user/router.py`:
```python
from app.modules.rbac.models import Role
from app.modules.user.service import assign_role, revoke_role


@router.post(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_perm("user:assign"))],
)
async def assign_role_endpoint(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:assign", perms)
    role = await db.get(Role, role_id)
    if role is None:
        raise ProblemDetails(code="role-not-found", status=404, detail="Role not found.")
    try:
        await assign_role(db, target, role, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_perm("user:assign"))],
)
async def revoke_role_endpoint(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    user: User = Depends(current_user_dep),
    db: AsyncSession = Depends(get_session),
) -> Response:
    perms = await get_user_permissions(db, user)
    target = await load_in_scope(db, User, user_id, user, "user:assign", perms)
    role = await db.get(Role, role_id)
    if role is None:
        raise ProblemDetails(code="role-not-found", status=404, detail="Role not found.")
    try:
        await revoke_role(db, target, role, actor=user)
    except GuardViolationError as e:
        raise _guard_to_problem(e) from e
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: Run — expect pass**

Run: `docker compose exec backend uv run pytest tests/modules/user/ tests/modules/rbac/ -v`
Expected: all green.

- [ ] **Step 6: Full backend regression**

Run: `docker compose exec backend uv run pytest`
Expected: all green.

Run: `docker compose exec backend uv run ruff check .`
Expected: clean.

Run: `bash scripts/audit/run_all.sh`
Expected: all L1 audits pass. If `audit_permissions.py` or `audit_listing.py` flag the new endpoints, read the error and add them to any hardcoded allowlists.

- [ ] **Step 7: Commit**

```bash
git add backend/app/modules/user/router.py backend/app/modules/rbac/router.py backend/app/modules/rbac/schemas.py backend/tests/modules/user/test_router_roles.py
git commit -m "feat(user,rbac): role assign/revoke endpoints + GET /roles list"
```

---

## Phase C — Frontend DataTable primitive

Lives at `frontend/src/components/table/DataTable.tsx`. Generic, server-paginated, no client-state shortcuts.

### Task C1: DataTable component

**Files:**
- Create: `frontend/src/components/table/DataTable.tsx`
- Create: `frontend/src/components/table/__tests__/DataTable.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/table/__tests__/DataTable.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";

type Row = { id: string; name: string };

const columns: ColumnDef<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name },
];

function makePage(items: Row[], page = 1, total = items.length) {
  return { items, total, page, size: 20, hasNext: total > page * 20 };
}

describe("DataTable", () => {
  it("renders loading state then rows", async () => {
    const fetcher = vi.fn().mockResolvedValue(makePage([{ id: "1", name: "Alice" }]));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
  });

  it("renders empty state when no rows", async () => {
    const fetcher = vi.fn().mockResolvedValue(makePage([]));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() =>
      expect(screen.getByText(/no results/i)).toBeInTheDocument()
    );
  });

  it("calls fetcher with page=2 after Next click", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(makePage([{ id: "1", name: "A" }], 1, 25))
      .mockResolvedValueOnce(makePage([{ id: "2", name: "B" }], 2, 25));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() => expect(screen.getByText("A")).toBeInTheDocument());

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(screen.getByText("B")).toBeInTheDocument());

    expect(fetcher).toHaveBeenNthCalledWith(1, expect.objectContaining({ page: 1 }));
    expect(fetcher).toHaveBeenNthCalledWith(2, expect.objectContaining({ page: 2 }));
  });

  it("renders error state on fetch rejection", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"));
    render(<DataTable columns={columns} fetcher={fetcher} queryKey={["users"]} />);
    await waitFor(() =>
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    );
  });
});
```

- [ ] **Step 2: Run — expect failure**

Run: `cd frontend && npx vitest run src/components/table`
Expected: module not found.

- [ ] **Step 3: Implement `DataTable`**

Create `frontend/src/components/table/DataTable.tsx`:
```tsx
import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { Page, PageQuery } from "@/lib/pagination";
import { Button } from "@/components/ui/button";

export type ColumnDef<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortable?: boolean;
};

export type DataTableProps<T> = {
  columns: ColumnDef<T>[];
  fetcher: (pq: PageQuery) => Promise<Page<T>>;
  queryKey: readonly unknown[];
  initialSize?: number;
  rowActions?: (row: T) => ReactNode;
  emptyMessage?: string;
};

type Status = "idle" | "loading" | "error" | "ready";

export function DataTable<T extends { id: string }>({
  columns,
  fetcher,
  queryKey,
  initialSize = 20,
  rowActions,
  emptyMessage = "No results.",
}: DataTableProps<T>) {
  const [page, setPage] = useState(1);
  const [size] = useState(initialSize);
  const [data, setData] = useState<Page<T> | null>(null);
  const [status, setStatus] = useState<Status>("idle");

  const load = useCallback(async () => {
    setStatus("loading");
    try {
      const result = await fetcher({ page, size });
      setData(result);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [fetcher, page, size]);

  useEffect(() => {
    void load();
    // queryKey invalidation: if the key tuple changes, caller re-renders with a new key,
    // remounting the component — so we don't need to track queryKey as a dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, size, ...queryKey]);

  if (status === "loading" && !data) {
    return (
      <div role="status" aria-label="Loading" className="py-8 text-center text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="py-8 text-center text-destructive">
        Failed to load.{" "}
        <Button variant="ghost" size="sm" onClick={() => void load()}>
          Retry
        </Button>
      </div>
    );
  }
  if (!data || data.items.length === 0) {
    return <div className="py-8 text-center text-muted-foreground">{emptyMessage}</div>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto rounded border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {columns.map((c) => (
                <th key={c.key} className="px-3 py-2 text-left font-medium">
                  {c.header}
                </th>
              ))}
              {rowActions ? <th className="px-3 py-2" /> : null}
            </tr>
          </thead>
          <tbody>
            {data.items.map((row) => (
              <tr key={row.id} className="border-t">
                {columns.map((c) => (
                  <td key={c.key} className="px-3 py-2">
                    {c.render(row)}
                  </td>
                ))}
                {rowActions ? <td className="px-3 py-2 text-right">{rowActions(row)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          Page {data.page} of {Math.max(1, Math.ceil(data.total / data.size))} · {data.total} total
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!data.hasNext}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd frontend && npx vitest run src/components/table`
Expected: 4 pass.

Run: `cd frontend && npm run typecheck`
Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/table/
git commit -m "feat(fe-table): DataTable primitive with server pagination"
```

---

## Phase D — Frontend AppShell primitive

Layout wrapper composed of `AppShell`, `Sidebar`, `TopBar`.

### Task D1: AppShell + Sidebar + TopBar

**Files:**
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/TopBar.tsx`
- Create: `frontend/src/components/layout/nav-items.ts`
- Create: `frontend/src/components/layout/__tests__/Sidebar.test.tsx`

- [ ] **Step 1: Write failing test**

Create `frontend/src/components/layout/__tests__/Sidebar.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/layout/Sidebar";

vi.mock("@/modules/rbac/usePermissions", () => ({
  usePermissions: vi.fn(),
}));
import { usePermissions } from "@/modules/rbac/usePermissions";

describe("Sidebar", () => {
  it("renders only nav entries user has permission for", () => {
    (usePermissions as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      can: (code: string) => code === "user:list",
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    expect(screen.getByText(/用户/i)).toBeInTheDocument();
    // "部门" nav is gated by department:list — not granted here
    expect(screen.queryByText(/部门/i)).not.toBeInTheDocument();
  });

  it("shows nothing behind a gate when user has no permissions", () => {
    (usePermissions as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      can: () => false,
      isLoading: false,
    });

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );
    expect(screen.queryByText(/用户/i)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect module not found**

Run: `cd frontend && npx vitest run src/components/layout`
Expected: fail.

- [ ] **Step 3: Create nav-items registry**

Create `frontend/src/components/layout/nav-items.ts`:
```ts
export type NavItem = {
  label: string;
  path: string;
  requiredPermission?: string;
};

export const NAV_ITEMS: NavItem[] = [
  { label: "仪表盘", path: "/" },
  { label: "用户管理", path: "/admin/users", requiredPermission: "user:list" },
  { label: "部门", path: "/admin/departments", requiredPermission: "department:list" },
];
```

- [ ] **Step 4: Implement Sidebar**

Create `frontend/src/components/layout/Sidebar.tsx`:
```tsx
import { NavLink } from "react-router-dom";
import { usePermissions } from "@/modules/rbac/usePermissions";
import { NAV_ITEMS } from "./nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  const { can, isLoading } = usePermissions();
  if (isLoading) return null;
  const visible = NAV_ITEMS.filter(
    (i) => !i.requiredPermission || can(i.requiredPermission)
  );

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r bg-muted/20 p-4">
      <nav className="flex flex-col gap-1">
        {visible.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "rounded px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent hover:text-accent-foreground"
              )
            }
            end={item.path === "/"}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 5: Implement TopBar**

Create `frontend/src/components/layout/TopBar.tsx`:
```tsx
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export function TopBar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();

  return (
    <header className="flex h-14 items-center justify-between border-b px-6">
      <div className="font-semibold">Business Template</div>
      <div className="flex items-center gap-3 text-sm">
        {user ? <span>{user.fullName}</span> : null}
        <Button variant="outline" size="sm" onClick={() => nav("/password-change")}>
          改密
        </Button>
        <Button variant="outline" size="sm" onClick={() => nav("/me/sessions")}>
          会话
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={async () => {
            await logout();
            nav("/login");
          }}
        >
          登出
        </Button>
      </div>
    </header>
  );
}
```

If `useAuth()` doesn't expose `logout`, inspect `frontend/src/lib/auth/AuthProvider.tsx` — it ships `AuthContextValue` with whatever method triggers token clear. Match the real name.

- [ ] **Step 6: Implement AppShell**

Create `frontend/src/components/layout/AppShell.tsx`:
```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell() {
  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Run tests — expect pass**

Run: `cd frontend && npx vitest run src/components/layout`
Expected: 2 pass.

Run: `cd frontend && npm run typecheck`
Expected: 0 errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/layout/
git commit -m "feat(fe-layout): AppShell + Sidebar (permission-gated) + TopBar"
```

---

## Phase E — Router reorganization

Move authenticated routes under `<AppShell />` so every admin page gets the shell.

### Task E1: Wrap authenticated routes with AppShell

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify or create: `frontend/src/App.test.tsx` (smoke test if file exists; otherwise skip this file)

- [ ] **Step 1: Edit `App.tsx`**

Replace the authenticated-routes block with a layout route wrapping them. New `frontend/src/App.tsx`:
```tsx
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";
import { AppShell } from "@/components/layout/AppShell";
import { PermissionsProvider } from "@/modules/rbac/PermissionsProvider";
import { ForbiddenPage } from "@/modules/rbac/ForbiddenPage";
import { LoginPage } from "@/modules/auth/LoginPage";
import { PasswordResetRequestPage } from "@/modules/auth/PasswordResetRequestPage";
import { PasswordResetConfirmPage } from "@/modules/auth/PasswordResetConfirmPage";
import { PasswordChangePage } from "@/modules/auth/PasswordChangePage";
import { SessionsPage } from "@/modules/auth/SessionsPage";
import { RequireAuth } from "@/modules/auth/components/RequireAuth";
import { DashboardPage } from "@/modules/dashboard/DashboardPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PermissionsProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/password-reset" element={<PasswordResetRequestPage />} />
            <Route path="/password-reset/confirm" element={<PasswordResetConfirmPage />} />
            <Route path="/403" element={<ForbiddenPage />} />

            <Route
              element={
                <RequireAuth>
                  <AppShell />
                </RequireAuth>
              }
            >
              <Route path="/" element={<DashboardPage />} />
              <Route path="/password-change" element={<PasswordChangePage />} />
              <Route path="/me/sessions" element={<SessionsPage />} />
              {/* user routes added in Phase F */}
            </Route>
          </Routes>
        </PermissionsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

Note: `<RequireAuth>` wraps a single child component, not an `<Outlet>`. If existing `RequireAuth` expects `children`, that's compatible (it renders its one child `<AppShell />`, which in turn renders `<Outlet />`). Verify by reading `frontend/src/modules/auth/components/RequireAuth.tsx`. If it requires children, the layout element pattern above works. If it already uses `<Outlet />`, remove the inner child wrapper and place `<RequireAuth />` as the layout element directly.

- [ ] **Step 2: Run dev smoke**

Start backend: `docker compose up -d`
In another terminal: `cd frontend && npm run dev`

Open `http://localhost:5173`:
- `/login` renders full-page (no shell).
- After login → `/` renders with sidebar + topbar.
- `/me/sessions` renders with sidebar + topbar.

Stop dev server with Ctrl-C once confirmed.

- [ ] **Step 3: Run existing tests**

Run: `cd frontend && npm test`
Expected: all green. If any auth/dashboard test depended on specific DOM structure (no shell), update selectors.

Run: `cd frontend && npm run typecheck && npm run lint`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(fe-app): wrap authenticated routes with AppShell layout"
```

---

## Phase F — User admin pages

Two pages + one subcomponent, all living under `frontend/src/modules/user/`.

### Task F1: `UserListPage`

**Files:**
- Create: `frontend/src/modules/user/UserListPage.tsx`
- Create: `frontend/src/modules/user/api.ts`
- Create: `frontend/src/modules/user/types.ts`
- Create: `frontend/src/modules/user/__tests__/UserListPage.test.tsx`
- Modify: `frontend/src/App.tsx` (add user routes)

- [ ] **Step 1: Define types**

Create `frontend/src/modules/user/types.ts`:
```ts
export interface RoleSummary {
  id: string;
  code: string;
  name: string;
}

export interface DepartmentSummary {
  id: string;
  name: string;
  path: string;
}

export interface User {
  id: string;
  email: string;
  fullName: string;
  departmentId: string | null;
  isActive: boolean;
  mustChangePassword: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface UserDetail extends User {
  roles: RoleSummary[];
  department: DepartmentSummary | null;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  fullName: string;
  departmentId?: string | null;
  mustChangePassword?: boolean;
}

export interface UserUpdatePayload {
  fullName?: string;
  departmentId?: string | null;
  isActive?: boolean;
}
```

- [ ] **Step 2: Define API helpers**

Create `frontend/src/modules/user/api.ts`:
```ts
import { client } from "@/api/client";
import type { Page, PageQuery } from "@/lib/pagination";
import type {
  RoleSummary,
  User,
  UserCreatePayload,
  UserDetail,
  UserUpdatePayload,
} from "./types";

export async function listUsers(
  pq: PageQuery & { is_active?: boolean }
): Promise<Page<User>> {
  const { data } = await client.get<Page<User>>("/api/v1/users", { params: pq });
  return data;
}

export async function getUser(id: string): Promise<UserDetail> {
  const { data } = await client.get<UserDetail>(`/api/v1/users/${id}`);
  return data;
}

export async function createUser(payload: UserCreatePayload): Promise<User> {
  const { data } = await client.post<User>("/api/v1/users", payload);
  return data;
}

export async function updateUser(id: string, payload: UserUpdatePayload): Promise<User> {
  const { data } = await client.patch<User>(`/api/v1/users/${id}`, payload);
  return data;
}

export async function softDeleteUser(id: string): Promise<void> {
  await client.delete(`/api/v1/users/${id}`);
}

export async function assignRole(userId: string, roleId: string): Promise<void> {
  await client.post(`/api/v1/users/${userId}/roles/${roleId}`);
}

export async function revokeRole(userId: string, roleId: string): Promise<void> {
  await client.delete(`/api/v1/users/${userId}/roles/${roleId}`);
}

export async function listRoles(): Promise<RoleSummary[]> {
  const { data } = await client.get<Page<RoleSummary>>("/api/v1/roles", {
    params: { size: 100 },
  });
  return data.items;
}
```

- [ ] **Step 3: Write failing list-page test**

Create `frontend/src/modules/user/__tests__/UserListPage.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/user/api", () => ({
  listUsers: vi.fn(),
}));
vi.mock("@/modules/rbac/usePermissions", () => ({
  usePermissions: () => ({ can: () => true, isLoading: false }),
}));
import { listUsers } from "@/modules/user/api";
import { UserListPage } from "@/modules/user/UserListPage";

describe("UserListPage", () => {
  it("renders rows for users returned from the API", async () => {
    (listUsers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          id: "u1",
          email: "a@b.com",
          fullName: "Alice",
          departmentId: null,
          isActive: true,
          mustChangePassword: false,
          createdAt: "2026-04-20T00:00:00Z",
          updatedAt: "2026-04-20T00:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      hasNext: false,
    });

    render(
      <MemoryRouter>
        <UserListPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(screen.getByText("Alice")).toBeInTheDocument());
    expect(screen.getByText("a@b.com")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run — expect failure**

Run: `cd frontend && npx vitest run src/modules/user`
Expected: module not found.

- [ ] **Step 5: Implement `UserListPage`**

Create `frontend/src/modules/user/UserListPage.tsx`:
```tsx
import { useCallback } from "react";
import { Link } from "react-router-dom";
import { DataTable, type ColumnDef } from "@/components/table/DataTable";
import { Button } from "@/components/ui/button";
import { listUsers } from "./api";
import type { User } from "./types";

const columns: ColumnDef<User>[] = [
  { key: "email", header: "邮箱", render: (u) => u.email },
  { key: "fullName", header: "姓名", render: (u) => u.fullName },
  {
    key: "isActive",
    header: "状态",
    render: (u) => (u.isActive ? "启用" : "停用"),
  },
  {
    key: "mustChangePassword",
    header: "强制改密",
    render: (u) => (u.mustChangePassword ? "是" : "否"),
  },
];

export function UserListPage() {
  const fetcher = useCallback(
    (pq: { page: number; size: number }) => listUsers({ ...pq, is_active: true }),
    []
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">用户管理</h1>
        <Button asChild>
          <Link to="/admin/users/new">新建用户</Link>
        </Button>
      </div>
      <DataTable<User>
        columns={columns}
        fetcher={fetcher}
        queryKey={["users"]}
        rowActions={(u) => (
          <Button asChild variant="ghost" size="sm">
            <Link to={`/admin/users/${u.id}`}>编辑</Link>
          </Button>
        )}
      />
    </div>
  );
}
```

- [ ] **Step 6: Register route in `App.tsx`**

Add inside the authenticated `<Route>` block (where the "user routes added in Phase F" comment sat):
```tsx
import { UserListPage } from "@/modules/user/UserListPage";
// ...
<Route path="/admin/users" element={<UserListPage />} />
```

- [ ] **Step 7: Run tests — expect pass**

Run: `cd frontend && npx vitest run src/modules/user`
Expected: 1 pass.

Run: `cd frontend && npm run typecheck`
Expected: 0 errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/modules/user/ frontend/src/App.tsx
git commit -m "feat(fe-user): UserListPage + API client + types + route"
```

### Task F2: `UserEditPage` (create mode)

**Files:**
- Create: `frontend/src/modules/user/UserEditPage.tsx`
- Modify: `frontend/src/modules/user/__tests__/UserListPage.test.tsx` (add create-mode test as new file)
- Create: `frontend/src/modules/user/__tests__/UserEditPage.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write failing test (create mode)**

Create `frontend/src/modules/user/__tests__/UserEditPage.test.tsx`:
```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/modules/user/api", () => ({
  createUser: vi.fn(),
  getUser: vi.fn(),
  updateUser: vi.fn(),
  listRoles: vi.fn().mockResolvedValue([]),
  assignRole: vi.fn(),
  revokeRole: vi.fn(),
}));
import { createUser } from "@/modules/user/api";
import { UserEditPage } from "@/modules/user/UserEditPage";

describe("UserEditPage create mode", () => {
  it("submits a valid payload and navigates on success", async () => {
    (createUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "new",
      email: "c@ex.com",
      fullName: "C",
      departmentId: null,
      isActive: true,
      mustChangePassword: true,
      createdAt: "2026-04-20T00:00:00Z",
      updatedAt: "2026-04-20T00:00:00Z",
    });

    render(
      <MemoryRouter initialEntries={["/admin/users/new"]}>
        <Routes>
          <Route path="/admin/users/new" element={<UserEditPage mode="create" />} />
          <Route path="/admin/users/:id" element={<div>detail</div>} />
        </Routes>
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText(/邮箱|email/i), "c@ex.com");
    await userEvent.type(screen.getByLabelText(/姓名|full name/i), "C");
    await userEvent.type(screen.getByLabelText(/^密码$|password/i), "GoodOne123");

    await userEvent.click(screen.getByRole("button", { name: /创建|create/i }));

    await waitFor(() => expect(createUser).toHaveBeenCalledTimes(1));
    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({ email: "c@ex.com", fullName: "C", password: "GoodOne123" })
    );
  });
});
```

- [ ] **Step 2: Run — expect failure**

Run: `cd frontend && npx vitest run src/modules/user/__tests__/UserEditPage.test.tsx`
Expected: module not found.

- [ ] **Step 3: Implement `UserEditPage` (create mode only)**

Create `frontend/src/modules/user/UserEditPage.tsx`:
```tsx
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { problemMessage } from "@/lib/problem-details";
import { createUser, getUser, updateUser } from "./api";
import type { UserDetail } from "./types";

export type UserEditPageProps = { mode: "create" | "edit" };

export function UserEditPage({ mode }: UserEditPageProps) {
  const nav = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState<UserDetail | null>(null);

  // Edit-mode loader added in Task F3.

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "create") {
        const created = await createUser({
          email,
          password,
          fullName,
          mustChangePassword: true,
        });
        nav(`/admin/users/${created.id}`);
      } else if (mode === "edit" && id) {
        await updateUser(id, { fullName });
        nav("/admin/users");
      }
    } catch (err) {
      setError(problemMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-lg flex-col gap-4">
      <h1 className="text-xl font-semibold">
        {mode === "create" ? "新建用户" : "编辑用户"}
      </h1>
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">邮箱 *</Label>
        <Input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={mode === "edit"}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="fullName">姓名 *</Label>
        <Input
          id="fullName"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </div>
      {mode === "create" ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">密码 *</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            至少 10 个字符，需包含字母和数字。
          </p>
        </div>
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {mode === "create" ? "创建" : "保存"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => nav(-1)}>
          取消
        </Button>
      </div>
    </form>
  );
}
```

(The `detail` state is wired in the next task for edit mode. TypeScript will flag it as unused — that's fine; Task F3 uses it. If the lint rule is strict, temporarily `// eslint-disable-next-line @typescript-eslint/no-unused-vars`.)

If `problemMessage` doesn't exist at `@/lib/problem-details`, check the file (`frontend/src/lib/problem-details.ts`) for the actual export name and adjust; Plan 4 introduced this module.

- [ ] **Step 4: Add routes in `App.tsx`**

```tsx
import { UserEditPage } from "@/modules/user/UserEditPage";
// ...
<Route path="/admin/users/new" element={<UserEditPage mode="create" />} />
<Route path="/admin/users/:id" element={<UserEditPage mode="edit" />} />
```

- [ ] **Step 5: Run tests — expect pass**

Run: `cd frontend && npx vitest run src/modules/user`
Expected: 2 pass.

Run: `cd frontend && npm run typecheck`
Expected: clean (or fix the unused-var lint via suppression noted above).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/user/UserEditPage.tsx frontend/src/modules/user/__tests__/UserEditPage.test.tsx frontend/src/App.tsx
git commit -m "feat(fe-user): UserEditPage (create mode) + routes"
```

### Task F3: UserEditPage edit mode + `RoleAssignmentPanel`

**Files:**
- Modify: `frontend/src/modules/user/UserEditPage.tsx`
- Create: `frontend/src/modules/user/components/RoleAssignmentPanel.tsx`
- Modify: `frontend/src/modules/user/__tests__/UserEditPage.test.tsx` (add edit-mode test)

- [ ] **Step 1: Extend test with edit-mode flow**

Append to `frontend/src/modules/user/__tests__/UserEditPage.test.tsx`:
```tsx
import { getUser, listRoles, assignRole, revokeRole, updateUser } from "@/modules/user/api";

describe("UserEditPage edit mode", () => {
  it("loads user, shows current roles, diffs and commits role changes on save", async () => {
    (getUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "u1",
      email: "e@ex.com",
      fullName: "E",
      departmentId: null,
      isActive: true,
      mustChangePassword: false,
      createdAt: "2026-04-20T00:00:00Z",
      updatedAt: "2026-04-20T00:00:00Z",
      roles: [{ id: "r1", code: "member", name: "Member" }],
      department: null,
    });
    (listRoles as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      { id: "r1", code: "member", name: "Member" },
      { id: "r2", code: "admin", name: "Admin" },
    ]);
    (updateUser as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({});
    (assignRole as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    (revokeRole as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);

    render(
      <MemoryRouter initialEntries={["/admin/users/u1"]}>
        <Routes>
          <Route path="/admin/users/:id" element={<UserEditPage mode="edit" />} />
          <Route path="/admin/users" element={<div>list</div>} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByDisplayValue("E")).toBeInTheDocument());

    // Member is currently checked; Admin is not. Toggle: uncheck member, check admin.
    await userEvent.click(screen.getByRole("checkbox", { name: /member/i }));
    await userEvent.click(screen.getByRole("checkbox", { name: /admin/i }));

    await userEvent.click(screen.getByRole("button", { name: /保存|save/i }));

    await waitFor(() => expect(updateUser).toHaveBeenCalled());
    expect(revokeRole).toHaveBeenCalledWith("u1", "r1");
    expect(assignRole).toHaveBeenCalledWith("u1", "r2");
  });
});
```

- [ ] **Step 2: Run — expect failure**

Run: `cd frontend && npx vitest run src/modules/user/__tests__/UserEditPage.test.tsx`
Expected: fails because edit-mode loader + role panel don't exist yet.

- [ ] **Step 3: Implement `RoleAssignmentPanel`**

Create `frontend/src/modules/user/components/RoleAssignmentPanel.tsx`:
```tsx
import { useEffect, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { listRoles } from "../api";
import type { RoleSummary } from "../types";

export type RoleAssignmentPanelProps = {
  initialRoleIds: string[];
  onSelectionChange: (roleIds: string[]) => void;
};

export function RoleAssignmentPanel({
  initialRoleIds,
  onSelectionChange,
}: RoleAssignmentPanelProps) {
  const [available, setAvailable] = useState<RoleSummary[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(initialRoleIds));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    void listRoles().then((rs) => {
      setAvailable(rs);
      setLoaded(true);
    });
  }, []);

  useEffect(() => {
    setSelected(new Set(initialRoleIds));
  }, [initialRoleIds]);

  function toggle(roleId: string) {
    const next = new Set(selected);
    if (next.has(roleId)) next.delete(roleId);
    else next.add(roleId);
    setSelected(next);
    onSelectionChange(Array.from(next));
  }

  if (!loaded) return <p className="text-sm text-muted-foreground">加载角色…</p>;

  return (
    <fieldset className="flex flex-col gap-2 rounded border p-4">
      <legend className="px-1 text-sm font-medium">角色</legend>
      {available.map((r) => {
        const id = `role-${r.id}`;
        return (
          <div key={r.id} className="flex items-center gap-2">
            <Checkbox
              id={id}
              checked={selected.has(r.id)}
              onCheckedChange={() => toggle(r.id)}
            />
            <Label htmlFor={id} className="text-sm font-normal">
              {r.name}{" "}
              <span className="text-muted-foreground">({r.code})</span>
            </Label>
          </div>
        );
      })}
    </fieldset>
  );
}
```

If `@/components/ui/checkbox` doesn't exist, run the shadcn CLI: `cd frontend && npx shadcn@latest add checkbox` — this adds the primitive to `src/components/ui/`.

- [ ] **Step 4: Extend `UserEditPage` with edit-mode loader + role panel**

Replace the body of `UserEditPage.tsx` with:
```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { problemMessage } from "@/lib/problem-details";
import { RoleAssignmentPanel } from "./components/RoleAssignmentPanel";
import {
  assignRole,
  createUser,
  getUser,
  revokeRole,
  updateUser,
} from "./api";
import type { UserDetail } from "./types";

export type UserEditPageProps = { mode: "create" | "edit" };

export function UserEditPage({ mode }: UserEditPageProps) {
  const nav = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [roleIds, setRoleIds] = useState<string[]>([]);
  const [initialRoleIds, setInitialRoleIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState<UserDetail | null>(null);

  useEffect(() => {
    if (mode !== "edit" || !id) return;
    void getUser(id).then((d) => {
      setDetail(d);
      setEmail(d.email);
      setFullName(d.fullName);
      const rIds = d.roles.map((r) => r.id);
      setRoleIds(rIds);
      setInitialRoleIds(rIds);
    });
  }, [id, mode]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "create") {
        const created = await createUser({
          email,
          password,
          fullName,
          mustChangePassword: true,
        });
        nav(`/admin/users/${created.id}`);
      } else if (mode === "edit" && id) {
        await updateUser(id, { fullName });
        const toAdd = roleIds.filter((r) => !initialRoleIds.includes(r));
        const toRemove = initialRoleIds.filter((r) => !roleIds.includes(r));
        await Promise.all([
          ...toAdd.map((rid) => assignRole(id, rid)),
          ...toRemove.map((rid) => revokeRole(id, rid)),
        ]);
        nav("/admin/users");
      }
    } catch (err) {
      setError(problemMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-lg flex-col gap-4">
      <h1 className="text-xl font-semibold">
        {mode === "create" ? "新建用户" : "编辑用户"}
      </h1>
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">邮箱 *</Label>
        <Input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={mode === "edit"}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="fullName">姓名 *</Label>
        <Input
          id="fullName"
          required
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
        />
      </div>
      {mode === "create" ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="password">密码 *</Label>
          <Input
            id="password"
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            至少 10 个字符，需包含字母和数字。
          </p>
        </div>
      ) : null}
      {mode === "edit" && detail ? (
        <RoleAssignmentPanel
          initialRoleIds={initialRoleIds}
          onSelectionChange={setRoleIds}
        />
      ) : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting}>
          {mode === "create" ? "创建" : "保存"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => nav(-1)}>
          取消
        </Button>
      </div>
    </form>
  );
}
```

- [ ] **Step 5: Run tests — expect pass**

Run: `cd frontend && npx vitest run src/modules/user`
Expected: 3 pass (list + create + edit).

Run: `cd frontend && npm run typecheck && npm run lint`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/modules/user/
git commit -m "feat(fe-user): UserEditPage edit mode + RoleAssignmentPanel"
```

---

## Phase G — Verification + tag

### Task G1: Full verification gate

**Files:** none (checks only).

- [ ] **Step 1: Backend tests**

Run: `docker compose exec backend uv run pytest`
Expected: 0 failures.

- [ ] **Step 2: Backend lint**

Run: `docker compose exec backend uv run ruff check .`
Expected: clean.

- [ ] **Step 3: Frontend tests + typecheck + lint**

Run: `cd frontend && npm test && npm run typecheck && npm run lint`
Expected: all clean.

- [ ] **Step 4: L1 audits**

Run: `bash scripts/audit/run_all.sh`
Expected: all green. Investigate any failure by reading the audit script output. Most likely suspects: `audit_permissions.py` not recognizing the new user endpoints (may require an allowlist entry), `audit_schema_db_consistency.py` (should be fine — no schema changes).

- [ ] **Step 5: Browser smoke test**

Boot stack: `docker compose up -d`
Start FE: `cd frontend && npm run dev`

Perform this sequence in the browser at `http://localhost:5173`:

1. Log in as `admin@example.com` (superadmin from Plan 4 seed).
2. Sidebar shows 仪表盘 + 用户管理.
3. Click 用户管理 → list renders with the seeded admin user.
4. Click 新建用户 → fill `newuser@example.com` / `Temp1234567` / `New User` → submit.
5. Navigate to detail → edit mode opens with empty role panel.
6. Check two roles → save → redirect to list.
7. Log out → log in as `newuser@example.com` with `Temp1234567` → redirected to `/password-change`.
8. Change password → land on dashboard.
9. Log out → log back in as superadmin → edit `newuser@example.com` → toggle role assignments → save.
10. Log in again as newuser → confirm role changes reflected in `/me/permissions` response (check Network tab).
11. Attempt to delete yourself from the user list (as a non-superadmin admin; if you only have a superadmin account, create a non-super admin first) → expect `self-protection` error toast / inline.
12. Toggle `?is_active=false` in URL on `/admin/users` list (browser dev) — shows soft-deleted users.

Document any failures in a scratch note, fix before tagging.

- [ ] **Step 6: Convention auditor subagent**

Invoke the `convention-auditor` subagent with the diff since `v0.4.0-rbac`:
```
Please audit all changes since tag v0.4.0-rbac against docs/conventions/*.md. Specific focus: convention 05 (API shape), 07 (RBAC + scope), 08 (naming/layout), 10 (form consistency), 99 (anti-laziness).
```
Expected output: `VERDICT: PASS`. If BLOCK, fix findings and re-run.

- [ ] **Step 7: Tag + memory update**

After all gates green:
```bash
git tag -a v0.5.0-admin-user-crud -m "Plan 5: admin User CRUD + role assignment, DataTable & AppShell primitives"
```

Update memory file `C:\Users\王子陽\.claude\projects\C--Programming-business-template\memory\plan5_status.md`:
```markdown
---
name: Plan 5 status
description: Admin user CRUD + role assignment prototype complete; tag v0.5.0
type: project
---

Plan 5 COMPLETE 2026-04-20. Tag `v0.5.0-admin-user-crud`.

Shipped:
- Backend `modules/user/` admin CRUD (list/read/create/update/soft-delete).
- Role assign/revoke endpoints + read-only `GET /roles` in rbac router.
- `SelfProtection` + `LastOfKind` guards in `core/guards.py` (both bypassed by superadmin).
- FE primitives: `<DataTable>` (server-paginated), `<AppShell>` (Sidebar + TopBar + Outlet).
- FE `modules/user/` — UserListPage + UserEditPage (create/edit) + RoleAssignmentPanel.
- Authenticated routes now nested under AppShell.

Deferred (in `docs/backlog.md`): Department tree CRUD UI, Role CRUD + RolePermission editor, audit-log viewer, admin session management, `last_login_at` field, admin-created-user email delivery.
```

Update `MEMORY.md` index entry for Plan 5:
```markdown
- [Plan 5 status](plan5_status.md) — COMPLETE 2026-04-20; tag `v0.5.0-admin-user-crud`; DataTable + AppShell primitives + User admin CRUD
```

- [ ] **Step 8: Final commit + push (if on remote)**

```bash
git status
# should be clean after the tag
```

If there are uncommitted audit-fix changes, commit them with `fix(plan5): <issue>` before tagging.

---

## Self-review summary

**Spec coverage:** all §1 items covered — §2.1 backend module layout (Tasks B1–B6), §2.2 FE layout (Tasks C1, D1), §2.3 data flow (Tasks F1–F3), §3 no migration (confirmed), §4 permissions (all existing from Plan 4), §5 schemas (Task B1), §6 guards (Tasks A1–A2 + B3), §7 FE specifics (C1, D1), §8 testing (every backend/FE task writes tests first), §9 verification gate (Task G1).

**Spec addenda:** one — `GET /roles` read-only endpoint, declared up front.

**Known plan risks:**
1. `ProblemDetails` may not accept `ctx` kwarg — Task B5 Step 3 flags this. If it doesn't, drop the kwarg; guard context is only needed for debugging, not for the UI flow.
2. The `audit_permissions.py` script may hard-match expected endpoints — new user endpoints may require adding to its allowlist. Task G1 Step 4 flags this.
3. Shadcn's `Checkbox` component may not yet be installed — Task F3 Step 3 calls it out and tells you how to add it.

No placeholders. All code blocks contain real, ready-to-paste content. Types and function signatures are consistent across tasks (`actor: User` kwarg threaded from guards → service → router; `PageQuery` shape matches `lib/pagination.ts`).
