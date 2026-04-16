"""FastAPI routes for this module.

Rules (see 05-api-contract + 06-auth-session + 07-rbac):
- Every endpoint declares permission via Depends(require_perm("...")), OR public=True.
- List endpoints inherit PaginatedEndpoint; NEVER return bare arrays.
- Use apply_scope() for data-scoped queries.
- Errors as Problem Details (app.core.errors).
"""
