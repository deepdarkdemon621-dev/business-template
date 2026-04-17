#!/usr/bin/env python
"""Audit: list endpoints (GET on /<resource>) must return `Page[...]` or similar,
never bare list[...] or List[...].

Heuristic: scan router.py functions decorated with @router.get(path) where path
doesn't include an `{id}` segment, and check their return annotation.

Short-circuits to PASS when no router files exist.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"


def get_route_path(dec: ast.Call) -> str | None:
    if not dec.args:
        return None
    if isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        return dec.args[0].value
    return None


def is_list_path(path: str) -> bool:
    if "{" in path:
        return False
    segments = [s for s in path.strip("/").split("/") if s]
    if segments and segments[0] == "me" and len(segments) <= 2:
        return len(segments) == 2 and segments[1] != "profile"
    return True


def audit_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func = dec.func
                if isinstance(func, ast.Attribute) and func.attr == "get":
                    route = get_route_path(dec)
                    if route and is_list_path(route):
                        # Check return annotation
                        ann = node.returns
                        if ann is None:
                            violations.append(
                                f"{path.relative_to(ROOT)}:{node.lineno} "
                                f"list endpoint `{node.name}` has no return annotation"
                            )
                            continue
                        src = ast.unparse(ann)
                        if "Page" not in src:
                            violations.append(
                                f"{path.relative_to(ROOT)}:{node.lineno} "
                                f"list endpoint `{node.name}` returns `{src}`, expected Page[...]"
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
        print("List endpoints with non-paginated response type:")
        for v in all_violations:
            print("  " + v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
