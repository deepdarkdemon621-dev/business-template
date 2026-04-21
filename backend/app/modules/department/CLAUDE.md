# department/ — Agent guide

Admin CRUD over the `Department` SQLAlchemy model, which lives in `modules/rbac/models.py`.
This module does NOT own a model — it imports `Department` from rbac.

Endpoints: list (flat, paginated) / tree (non-paginated) / read / create / update / soft-delete / move.
All guarded by the `department:*` permissions seeded in migration 0005.

Materialized-path subtree rewrite + cycle detection live in `service.py::DepartmentService.move_department`.
Guards (`HasChildren`, `HasAssignedUsers`, `NoCycle`) are registered on `Department.__guards__` in `rbac/models.py`.
