"""RBAC service layer (stub).

Plan 4 routes all RBAC mutations through CLI commands
(`app/cli_commands/rbac.py`) and the seed migration; no web endpoints
mutate RBAC data yet. This file exists to satisfy the canonical
5-file module layout (convention 08) and is the designated home for
future HTTP-mutation business logic (grant/revoke role, create role,
create department, etc.) when Plan 5+ introduces admin UIs.
"""
