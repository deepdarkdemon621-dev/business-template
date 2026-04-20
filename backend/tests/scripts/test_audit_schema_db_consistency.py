"""Tests for scripts/audit/audit_schema_db_consistency.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

AUDIT_SCRIPT = Path("/scripts/audit/audit_schema_db_consistency.py")

pytestmark = pytest.mark.skipif(
    not AUDIT_SCRIPT.exists(),
    reason="audit_schema_db_consistency.py not mounted at /scripts (expected via docker-compose)",
)


def run_audit(cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def _write_fixture(
    root: Path,
    *,
    schemas: dict[str, str],
    migrations: dict[str, str],
) -> None:
    """Create a minimal backend-shaped tree at `root` for the audit to scan."""
    # audit_schema_db_consistency.py computes MODULES relative to its own
    # location (ROOT/.. /.. / backend / app / modules). That pathing is fixed,
    # so the test directly invokes the audit pointed at real ROOT. Instead we
    # monkey-patch by writing a tiny sibling audit runner in tmp_path.
    raise NotImplementedError  # not used — see run_with_overrides


def run_with_overrides(
    tmp_path: Path, *, schemas: str, migration: str
) -> subprocess.CompletedProcess:
    """Invoke the audit with MODULES/MIGRATIONS overridden to tmp_path trees."""
    modules_dir = tmp_path / "backend" / "app" / "modules" / "sample"
    modules_dir.mkdir(parents=True)
    (modules_dir / "schemas.py").write_text(schemas)

    migrations_dir = tmp_path / "backend" / "alembic" / "versions"
    migrations_dir.mkdir(parents=True)
    (migrations_dir / "0001_sample.py").write_text(migration)

    # Small shim: import the audit, rebind its globals, then call main([]).
    shim = tmp_path / "run_audit.py"
    shim.write_text(
        textwrap.dedent(
            f"""
            import sys
            from pathlib import Path
            sys.path.insert(0, "/scripts/audit")
            import importlib
            mod = importlib.import_module("audit_schema_db_consistency")
            mod.MODULES = Path({str(modules_dir)!r})
            mod.MIGRATIONS = Path({str(migrations_dir)!r})
            sys.exit(mod.main([]))
            """
        ).strip()
    )
    return subprocess.run(
        [sys.executable, str(shim)],
        capture_output=True,
        text=True,
    )


def test_flags_pydantic_wider_than_db(tmp_path: Path) -> None:
    schemas = textwrap.dedent(
        """
        from pydantic import BaseModel, Field

        class SampleCreate(BaseModel):
            name: str = Field(..., max_length=200)
        """
    )
    migration = textwrap.dedent(
        """
        def upgrade():
            op.create_table(
                "samples",
                sa.Column("id", sa.Integer(), nullable=False),
                sa.Column("name", sa.String(50), nullable=False),
            )
        """
    )
    result = run_with_overrides(tmp_path, schemas=schemas, migration=migration)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "SampleCreate.name" in result.stdout
    assert "200" in result.stdout
    assert "50" in result.stdout


def test_passes_when_pydantic_matches_db(tmp_path: Path) -> None:
    schemas = textwrap.dedent(
        """
        from pydantic import BaseModel, Field

        class SampleCreate(BaseModel):
            name: str = Field(..., max_length=50)
        """
    )
    migration = textwrap.dedent(
        """
        def upgrade():
            op.create_table(
                "samples",
                sa.Column("id", sa.Integer(), nullable=False),
                sa.Column("name", sa.String(50), nullable=False),
            )
        """
    )
    result = run_with_overrides(tmp_path, schemas=schemas, migration=migration)
    assert result.returncode == 0, result.stdout + result.stderr


def test_skips_when_no_matching_table(tmp_path: Path) -> None:
    schemas = textwrap.dedent(
        """
        from pydantic import BaseModel, Field

        class NestedDTOCreate(BaseModel):
            name: str = Field(..., max_length=9999)
        """
    )
    migration = textwrap.dedent(
        """
        def upgrade():
            op.create_table(
                "users",
                sa.Column("id", sa.Integer(), nullable=False),
            )
        """
    )
    result = run_with_overrides(tmp_path, schemas=schemas, migration=migration)
    assert result.returncode == 0, result.stdout + result.stderr
