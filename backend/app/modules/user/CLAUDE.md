# user/ — Agent guide

Admin CRUD over the `User` SQLAlchemy model, which lives in `modules/auth/models.py`.
This module does NOT own a model — it imports `User` from auth.

Endpoints: list / create / read / update / soft-delete; role assign / revoke.
All guarded by the `user:*` permissions seeded in Plan 4.

Self-protection and last-superadmin invariants are enforced via `__guards__` on the User model, registered in `app/modules/auth/models.py`.
