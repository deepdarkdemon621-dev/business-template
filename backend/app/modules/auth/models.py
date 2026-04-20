from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.guards import SelfProtection
from app.modules.rbac.constants import ScopeEnum
from app.modules.rbac.guards import LastOfKind


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list[UserSession]] = relationship(back_populates="user", cascade="all, delete")

    # Loaded via selectin so guards can read is_superadmin synchronously.
    # user_roles has two FKs to users (user_id + granted_by), so we must
    # name both join legs explicitly to avoid AmbiguousForeignKeysError.
    roles: Mapped[list[object]] = relationship(
        "Role",
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="UserRole.role_id == Role.id",
        lazy="selectin",
        viewonly=True,
    )

    @property
    def is_superadmin(self) -> bool:
        """True when the user holds at least one superadmin role."""
        return any(getattr(r, "is_superadmin", False) for r in self.roles)

    __scope_map__ = {
        ScopeEnum.DEPT_TREE: "department_id",
        ScopeEnum.DEPT: "department_id",
        ScopeEnum.OWN: "id",
    }

    __guards__ = {
        "delete": [SelfProtection()],
        "deactivate": [SelfProtection()],
        "strip_role": [SelfProtection(), LastOfKind("superadmin")],
    }


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user: Mapped[User] = relationship(back_populates="sessions")
