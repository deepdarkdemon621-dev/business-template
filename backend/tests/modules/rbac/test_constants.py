from app.modules.rbac.constants import ScopeEnum, scope_priority, widest


def test_scope_priority_ordering():
    assert scope_priority(ScopeEnum.GLOBAL) > scope_priority(ScopeEnum.DEPT_TREE)
    assert scope_priority(ScopeEnum.DEPT_TREE) > scope_priority(ScopeEnum.DEPT)
    assert scope_priority(ScopeEnum.DEPT) > scope_priority(ScopeEnum.OWN)


def test_widest_returns_highest_priority():
    assert widest(ScopeEnum.OWN, ScopeEnum.DEPT_TREE) == ScopeEnum.DEPT_TREE
    assert widest(ScopeEnum.GLOBAL, ScopeEnum.DEPT) == ScopeEnum.GLOBAL
    assert widest(ScopeEnum.OWN, ScopeEnum.OWN) == ScopeEnum.OWN


def test_action_enum_includes_move() -> None:
    from app.modules.rbac.constants import ActionEnum

    assert ActionEnum.MOVE == "move"
    assert "move" in {a.value for a in ActionEnum}
