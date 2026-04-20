from app.modules.auth.models import User
from app.modules.rbac.constants import ScopeEnum


def test_user_has_scope_map():
    assert hasattr(User, "__scope_map__")
    m = User.__scope_map__
    assert m[ScopeEnum.DEPT_TREE] == "department_id"
    assert m[ScopeEnum.DEPT] == "department_id"
    assert m[ScopeEnum.OWN] == "id"
