from __future__ import annotations

from typing import Any

_SENSITIVE_KEY_FRAGMENTS = ("password", "token", "secret", "api_key")


def _is_sensitive_key(key: str) -> bool:
    low = key.lower()
    return any(frag in low for frag in _SENSITIVE_KEY_FRAGMENTS)


def _strip_sensitive(value: Any) -> Any:
    """Recursively remove any key matching sensitive patterns from dicts / lists of dicts."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _strip_sensitive(v) for k, v in value.items() if not _is_sensitive_key(k)}
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


def _diff_dict(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Return {field: [old, new]} for keys whose values differ. Missing side = None."""
    keys = set(before) | set(after)
    out: dict[str, list[Any]] = {}
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            out[k] = [b, a]
    return out
