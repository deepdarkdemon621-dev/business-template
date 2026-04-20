from __future__ import annotations

from enum import StrEnum


class ScopeEnum(StrEnum):
    GLOBAL = "global"
    DEPT_TREE = "dept_tree"
    DEPT = "dept"
    OWN = "own"


class ActionEnum(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LIST = "list"
    EXPORT = "export"
    APPROVE = "approve"
    REJECT = "reject"
    PUBLISH = "publish"
    INVOKE = "invoke"
    ASSIGN = "assign"


_SCOPE_PRIORITY: dict[ScopeEnum, int] = {
    ScopeEnum.GLOBAL: 3,
    ScopeEnum.DEPT_TREE: 2,
    ScopeEnum.DEPT: 1,
    ScopeEnum.OWN: 0,
}


def scope_priority(scope: ScopeEnum) -> int:
    return _SCOPE_PRIORITY[scope]


def widest(a: ScopeEnum, b: ScopeEnum) -> ScopeEnum:
    return a if _SCOPE_PRIORITY[a] >= _SCOPE_PRIORITY[b] else b


# Sentinel returned by get_user_permissions for superadmins — callers short-circuit.
SUPERADMIN_ALL = object()
