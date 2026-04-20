"""Tests for scripts/audit/audit_scope.py.

The audit script lives at the project root under `scripts/audit/`, which the
docker compose config mounts read-only at `/scripts` inside the backend
container. These tests invoke the script via a subprocess so that the exit
code and stdout are exercised exactly as run_all.sh would see them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

AUDIT_SCRIPT = Path("/scripts/audit/audit_scope.py")

pytestmark = pytest.mark.skipif(
    not AUDIT_SCRIPT.exists(),
    reason="audit_scope.py not mounted at /scripts (expected via docker-compose)",
)


def run_audit(target_files: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), *map(str, target_files)],
        capture_output=True,
        text=True,
    )


def test_audit_flags_missing_apply_scope(tmp_path: Path) -> None:
    p = tmp_path / "bad.py"
    p.write_text(
        """
from fastapi import APIRouter
from sqlalchemy import select
from app.modules.auth.models import User
router = APIRouter()

@router.get("/bad")
async def bad(db):
    stmt = select(User)
    result = await db.execute(stmt)
    return result.scalars().all()
"""
    )
    result = run_audit([p])
    assert result.returncode == 1, result.stdout + result.stderr
    assert "scope" in result.stdout.lower()


def test_audit_passes_when_apply_scope_present(tmp_path: Path) -> None:
    p = tmp_path / "good.py"
    p.write_text(
        """
from fastapi import APIRouter
from sqlalchemy import select
from app.core.permissions import apply_scope
from app.modules.auth.models import User
router = APIRouter()

@router.get("/good")
async def good(db, user):
    stmt = select(User)
    stmt = apply_scope(stmt, user, "user:list", User, {})
    result = await db.execute(stmt)
    return list(result.scalars().all())
"""
    )
    result = run_audit([p])
    assert result.returncode == 0, result.stdout + result.stderr


def test_audit_ignores_unscoped_models(tmp_path: Path) -> None:
    p = tmp_path / "other.py"
    p.write_text(
        """
from fastapi import APIRouter
from sqlalchemy import select
from some.module import SomeOtherModel
router = APIRouter()

@router.get("/other")
async def other(db):
    stmt = select(SomeOtherModel)
    return (await db.execute(stmt)).scalars().all()
"""
    )
    result = run_audit([p])
    assert result.returncode == 0, result.stdout + result.stderr


def test_audit_respects_ignore_comment(tmp_path: Path) -> None:
    p = tmp_path / "ignored.py"
    p.write_text(
        """
from fastapi import APIRouter
from sqlalchemy import select
from app.modules.auth.models import User
router = APIRouter()

@router.get("/me")
async def me(db):
    # audit-scope: ignore - user viewing themselves is always in scope
    stmt = select(User)
    return (await db.execute(stmt)).scalars().all()
"""
    )
    result = run_audit([p])
    assert result.returncode == 0, result.stdout + result.stderr
