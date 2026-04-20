#!/usr/bin/env python
"""Audit: every FastAPI route function must have either
  - a dependency Depends(require_perm(...)) / Depends(require_auth) / Depends(load_in_scope(...))
  - OR an explicit public=True marker in its decorator kwargs

Runs an AST scan over backend/app/modules/*/router.py files.
Since Plan 1 has no router files yet, the script short-circuits to PASS in absence of routers.
Plan 3+ adds real routers; the script then becomes active.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def is_route_decorator(dec: ast.expr) -> tuple[bool, ast.Call | None]:
    if isinstance(dec, ast.Call):
        func = dec.func
        attr = None
        if isinstance(func, ast.Attribute):
            attr = func.attr
        if attr in HTTP_METHODS:
            return True, dec
    return False, None


AUTH_DEP_MARKERS = {
    "require_perm", "require_auth", "load_in_scope",
    "get_current_user", "_current_user", "public_endpoint",
    "current_user_dep",
}


def has_permission_dep(call: ast.Call, func_node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for kw in call.keywords:
        if kw.arg == "dependencies":
            if isinstance(kw.value, ast.List):
                for el in kw.value.elts:
                    src = ast.unparse(el)
                    if any(m in src for m in AUTH_DEP_MARKERS):
                        return True
        if kw.arg == "public":
            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    for arg in func_node.args.args + func_node.args.kwonlyargs:
        if arg.annotation:
            src = ast.unparse(arg.annotation)
            if any(m in src for m in AUTH_DEP_MARKERS):
                return True
    for default in func_node.args.defaults + func_node.args.kw_defaults:
        if default is not None:
            src = ast.unparse(default)
            if any(m in src for m in AUTH_DEP_MARKERS):
                return True
    return False


def audit_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for dec in node.decorator_list:
                is_route, call = is_route_decorator(dec)
                if is_route and call is not None:
                    if not has_permission_dep(call, node):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno} "
                            f"endpoint `{node.name}` missing require_perm/public=True"
                        )
    return violations


def main() -> int:
    if not MODULES.exists():
        return 0
    router_files = list(MODULES.glob("*/router.py"))
    if not router_files:
        return 0

    all_violations: list[str] = []
    for f in router_files:
        all_violations.extend(audit_file(f))

    if all_violations:
        print("Endpoints missing permission/public marker:")
        for v in all_violations:
            print("  " + v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
