#!/usr/bin/env python
"""L1 audit: every route handler that selects a scoped model must call
apply_scope / load_in_scope (or explicitly opt out with an ignore comment).

Scans backend/app/modules/*/router.py from the project root.

Exit 0: clean. Exit 1: violations found (printed as file:line).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"

ROUTE_DECORATORS = {"get", "post", "put", "patch", "delete"}
SCOPED_MODELS = {"User", "Department"}  # extend when new models declare __scope_map__
SCOPE_CALLS = {"apply_scope", "load_in_scope"}
IGNORE_COMMENT = "audit-scope: ignore"


def iter_route_handlers(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ROUTE_DECORATORS:
                        yield node
                        break


def uses_scoped_model_query(fn: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, model_name) for each select(M) / db.get(M, ...) on a scoped model."""
    hits: list[tuple[int, str]] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            # select(M)
            if isinstance(node.func, ast.Name) and node.func.id == "select":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id in SCOPED_MODELS:
                        hits.append((node.lineno, arg.id))
            # db.get(M, ...)
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id in SCOPED_MODELS:
                        hits.append((node.lineno, arg.id))
    return hits


def has_scope_call(fn: ast.AST) -> bool:
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in SCOPE_CALLS:
                return True
            if isinstance(node.func, ast.Attribute) and node.func.attr in SCOPE_CALLS:
                return True
    return False


def has_ignore_comment(source_lines: list[str], lineno: int) -> bool:
    """Check whether the nearest preceding non-blank line contains the ignore marker."""
    for i in range(lineno - 2, max(-1, lineno - 6), -1):
        if i < 0 or i >= len(source_lines):
            break
        stripped = source_lines[i].strip()
        if not stripped:
            continue
        return IGNORE_COMMENT in stripped
    return False


def audit_file(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)
    violations: list[str] = []
    for fn in iter_route_handlers(tree):
        hits = uses_scoped_model_query(fn)
        if not hits:
            continue
        if has_scope_call(fn):
            continue
        if any(has_ignore_comment(lines, ln) for ln, _ in hits):
            continue
        models = ", ".join(sorted({m for _, m in hits}))
        violations.append(
            f"{path}:{fn.lineno} {fn.name}: missing apply_scope/load_in_scope "
            f"(uses {models})"
        )
    return violations


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        targets = [Path(p) for p in argv[1:]]
    else:
        if not MODULES.exists():
            return 0
        targets = list(MODULES.rglob("router.py"))
    violations: list[str] = []
    for p in targets:
        if p.exists():
            violations.extend(audit_file(p))
    for v in violations:
        print(v)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
