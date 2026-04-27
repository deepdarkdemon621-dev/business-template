from __future__ import annotations

from typing import Any

# Substring fragments. Matched case-insensitively against any dict key in
# audit payloads. Note the breadth: `token` will also strip a hypothetical
# `token_count` field; `password` will strip `last_password_change_at`. Audit
# data is a one-way write — silent loss is preferable to leaking credentials,
# but if a future analytics field collides, rename it or scope this list.
_SENSITIVE_KEY_FRAGMENTS = ("password", "token", "secret", "api_key")


def _is_sensitive_key(key: str) -> bool:
    low = key.lower()
    return any(frag in low for frag in _SENSITIVE_KEY_FRAGMENTS)


def _strip_sensitive(value: Any) -> Any:
    """Strip credential-bearing keys from audit payloads.

    Recursively walks dicts and lists-of-dicts, dropping any key whose name
    contains a sensitive fragment. Audit rows persist forever; a leaked
    password_hash or refresh_token in `before`/`after`/`changes` JSONB would
    be a permanent credential exposure.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _strip_sensitive(v) for k, v in value.items() if not _is_sensitive_key(k)}
    if isinstance(value, list):
        return [_strip_sensitive(item) for item in value]
    return value


def _diff_dict(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[Any]]:
    """Diff two snapshots into the shape stored in `audit_events.changes`.

    Returns {field: [old, new]} for keys whose values differ. Keys present
    on only one side are reported with `None` on the missing side.
    """
    keys = set(before) | set(after)
    out: dict[str, list[Any]] = {}
    for k in keys:
        b = before.get(k)
        a = after.get(k)
        if b != a:
            out[k] = [b, a]
    return out
