import pytest

from app.modules.audit.service import _diff_dict, _strip_sensitive

SENSITIVE_KEYS = {
    "password", "password_hash", "token", "refresh_token",
    "refresh_token_hash", "secret", "access_token", "reset_token", "api_key",
}


@pytest.mark.parametrize("key", list(SENSITIVE_KEYS))
def test_strip_removes_top_level_sensitive_key(key):
    out = _strip_sensitive({key: "x", "safe": 1})
    assert key not in out
    assert out["safe"] == 1


def test_strip_removes_nested_sensitive_key():
    inp = {"user": {"password_hash": "xxx", "email": "a@b.com"}}
    out = _strip_sensitive(inp)
    assert "password_hash" not in out["user"]
    assert out["user"]["email"] == "a@b.com"


def test_strip_walks_lists_of_dicts():
    inp = {"items": [{"token": "t1", "id": 1}, {"token": "t2", "id": 2}]}
    out = _strip_sensitive(inp)
    assert all("token" not in item for item in out["items"])
    assert [i["id"] for i in out["items"]] == [1, 2]


def test_strip_is_case_insensitive():
    inp = {"Password": "x", "ACCESS_TOKEN": "y", "refresh_TOKEN_hash": "z"}
    out = _strip_sensitive(inp)
    assert out == {}


def test_strip_on_none_returns_none():
    assert _strip_sensitive(None) is None


def test_diff_dict_only_includes_changed_keys():
    before = {"name": "A", "email": "a@x", "code": "X"}
    after = {"name": "B", "email": "a@x", "code": "X"}
    assert _diff_dict(before, after) == {"name": ["A", "B"]}


def test_diff_dict_handles_added_and_removed_keys():
    before = {"a": 1, "b": 2}
    after = {"b": 2, "c": 3}
    assert _diff_dict(before, after) == {"a": [1, None], "c": [None, 3]}


def test_diff_dict_empty_when_identical():
    assert _diff_dict({"x": 1}, {"x": 1}) == {}
