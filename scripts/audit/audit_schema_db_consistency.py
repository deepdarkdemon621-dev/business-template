#!/usr/bin/env python
"""L1 audit: Pydantic *Create / *Update schemas must not declare a wider
max_length than the corresponding Alembic column.

Mismatch pattern we catch: Pydantic accepts 200-char input, DB column is
sa.String(50) — the DB write will fail at runtime. We flag whenever
Pydantic.max_length > DB.max_length.

Strategy: parse each schemas.py for *Create/*Update classes and collect
their (field, max_length). Parse each alembic/versions/*.py for
create_table() blocks and collect (column, max_length). Diff.

The mapping Entity -> table is heuristic: RoleCreate -> `roles`, etc.
When no table matches we skip (avoids false positives on nested DTOs).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"
MIGRATIONS = ROOT / "backend" / "alembic" / "versions"


def _field_max_length(value: ast.expr | None) -> tuple[int | None, bool]:
    """Extract (max_length, required) from a Field(...) call or similar default."""
    max_length: int | None = None
    required = value is None  # bare annotation is required
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "Field":
        for kw in value.keywords:
            if kw.arg == "max_length" and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, int):
                    max_length = kw.value.value
        if value.args and isinstance(value.args[0], ast.Constant) and value.args[0].value is Ellipsis:
            required = True
    return max_length, required


def parse_pydantic_schemas(path: Path) -> dict[str, dict[str, dict]]:
    """Return {ClassName: {field: {'max_length': N|None, 'required': bool}}}."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, dict]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not (node.name.endswith("Create") or node.name.endswith("Update") or node.name.endswith("In")):
            continue
        fields: dict[str, dict] = {}
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                name = item.target.id
                max_length, required = _field_max_length(item.value)
                fields[name] = {"max_length": max_length, "required": required}
        out[node.name] = fields
    return out


_CREATE_TABLE_RE = re.compile(
    r'create_table\(\s*["\'](?P<table>\w+)["\']',
)
_COLUMN_RE = re.compile(
    r'sa\.Column\(\s*["\'](?P<col>\w+)["\']\s*,\s*sa\.String\((?P<len>\d+)\)'
    r'(?P<tail>[^)]*)\)',
)


def parse_migration_columns(migrations_dir: Path) -> dict[str, dict[str, dict]]:
    """Return {table_name: {column: {'max_length': N, 'nullable': bool}}}.

    Scans each migration file for `create_table("<name>", ...)` blocks and
    collects sa.Column("<col>", sa.String(N), ...) occurrences within them.
    """
    out: dict[str, dict[str, dict]] = {}
    if not migrations_dir.exists():
        return out
    for p in sorted(migrations_dir.glob("*.py")):
        src = p.read_text(encoding="utf-8")
        # Walk through create_table(...) blocks one at a time.
        pos = 0
        while True:
            m = _CREATE_TABLE_RE.search(src, pos)
            if not m:
                break
            table = m.group("table")
            # Find matching closing paren for this create_table call (balanced parens).
            start = m.end()
            depth = 1
            i = start
            while i < len(src) and depth > 0:
                c = src[i]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                i += 1
            body = src[start:i]
            for colm in _COLUMN_RE.finditer(body):
                nullable = True
                tail = colm.group("tail")
                nm = re.search(r"nullable\s*=\s*(True|False)", tail)
                if nm:
                    nullable = nm.group(1) == "True"
                out.setdefault(table, {})[colm.group("col")] = {
                    "max_length": int(colm.group("len")),
                    "nullable": nullable,
                }
            pos = i
    return out


def _guess_table(cls_name: str) -> list[str]:
    """Convert a schema class name like 'RoleCreate' into candidate table names."""
    base = cls_name
    for suffix in ("Create", "Update", "In"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower()
    return [snake + "s", snake]


def main(argv: list[str]) -> int:
    violations: list[str] = []

    pydantic_classes: dict[str, dict[str, dict]] = {}
    if MODULES.exists():
        for sp in MODULES.rglob("schemas.py"):
            pydantic_classes.update(parse_pydantic_schemas(sp))

    migration_cols = parse_migration_columns(MIGRATIONS)

    for cls_name, fields in pydantic_classes.items():
        candidates = _guess_table(cls_name)
        table = next((c for c in candidates if c in migration_cols), None)
        if table is None:
            continue
        for fname, fspec in fields.items():
            mcol = migration_cols[table].get(fname)
            if mcol is None:
                continue
            if fspec["max_length"] is not None and mcol["max_length"] is not None:
                if fspec["max_length"] > mcol["max_length"]:
                    violations.append(
                        f"{cls_name}.{fname}: Pydantic max_length="
                        f"{fspec['max_length']} > DB(`{table}`) "
                        f"max_length={mcol['max_length']} — input will be "
                        f"accepted but DB will reject."
                    )

    for v in violations:
        print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
