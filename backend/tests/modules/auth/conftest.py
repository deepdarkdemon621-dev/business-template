"""conftest for auth module tests.

Auth endpoint integration tests use the root conftest's `db_session` +
`client_with_db` fixtures (per-test transactional rollback). No module-local
schema setup or event-loop tweaks needed.
"""
