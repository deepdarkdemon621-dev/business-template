# rbac/ — Agent guide

Models: Department, Permission, Role, RolePermission, UserRole.
Cross-cutting utilities (`require_perm`, `apply_scope`, `load_in_scope`, `get_user_permissions`) live in `app/core/permissions.py`, NOT here.
This module owns only: entity models, schemas, CRUD, router, CLI subcommands.
