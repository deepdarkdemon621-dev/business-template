# Plan 3: Auth Module — Design Spec

> **Scope:** Authentication layer for a generic business back-office template. JWT access tokens, rotating refresh tokens, password hashing, login lockout, password reset with email, session management, captcha hook.
>
> **Not in scope (Plan 4):** RBAC, roles, permissions, `require_perm`, `apply_scope`, Department model.

## 1. Architecture: Core vs Module Split

Auth is split across two locations:

| Location | Responsibility |
|---|---|
| `app/core/auth.py` | Importable by any module. Password hashing, JWT encode/decode, `get_current_user` dependency, Redis denylist client, login lockout helpers, captcha hook. |
| `app/core/email.py` | Email delivery abstraction. Jinja2 templates + aiosmtplib, with console fallback in dev. |
| `app/modules/auth/` | Endpoint-facing. User model, UserSession model, schemas, service (login/refresh/logout/reset/sessions), router, CRUD. |

**Why split:** Other modules (Plan 4+) need `get_current_user` without importing the auth module. Core auth has zero dependency on `modules/auth/` — it receives a User object from the DB, it doesn't query for it. The `get_current_user` dependency does the DB lookup, but it imports the User model by string reference or deferred import to avoid circular deps.

## 2. Data Model

### 2.1 `users` table

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK, server default `gen_random_uuid()` | |
| `email` | `String(255)` | unique, not null, indexed | Login identifier |
| `password_hash` | `String(255)` | not null | Argon2 via passlib |
| `full_name` | `String(100)` | not null | Display name |
| `department_id` | `UUID` | nullable | Plain column, no FK constraint until Plan 4 adds Department model |
| `is_active` | `Boolean` | not null, default `True` | Soft disable |
| `must_change_password` | `Boolean` | not null, default `False` | Admin-created accounts |
| `created_at` | `DateTime(timezone=True)` | not null, server default `now()` | |
| `updated_at` | `DateTime(timezone=True)` | not null, server default `now()`, onupdate `now()` | |

**Extension policy:** New user profile fields (phone, employee_id, avatar_url, etc.) are added directly to this table via `ALTER TABLE ADD COLUMN`. Separate tables only for data with independent access patterns (preferences, audit logs).

### 2.2 `user_sessions` table

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | Same value as the refresh token `jti` |
| `user_id` | `UUID` | FK → users.id, not null, indexed | |
| `device_label` | `String(255)` | nullable | Extracted from `User-Agent` header |
| `ip_address` | `String(45)` | nullable | Client IP (supports IPv6) |
| `created_at` | `DateTime(timezone=True)` | not null, server default `now()` | |
| `last_used_at` | `DateTime(timezone=True)` | not null | Updated on each refresh |
| `expires_at` | `DateTime(timezone=True)` | not null | Absolute TTL = created_at + 7 days |

**No `is_revoked` column.** Revocation is handled by the Redis denylist. A revoked session's Redis key persists until the session's `expires_at`, after which the session row can be cleaned up.

### 2.3 Indexes

- `users.email` — unique index (login lookups)
- `user_sessions.user_id` — btree index (session listing per user)
- `user_sessions.expires_at` — btree index (cleanup queries)

## 3. Token Model

Per convention `06-auth-session.md`:

| Token | Lifetime | Storage | Transport |
|---|---|---|---|
| Access JWT | 30 min (`ACCESS_TOKEN_TTL_MINUTES`) | FE memory + sessionStorage | `Authorization: Bearer <token>` |
| Refresh token | 7 days absolute + 30 min idle | httpOnly; Secure; SameSite=Strict; Path=/api/v1/auth cookie | Automatic |

### 3.1 Access JWT Payload

```json
{
  "sub": "<user_uuid>",
  "role_ids": [],
  "dept_id": null,
  "jti": "<access_uuid>",
  "iat": 1700000000,
  "exp": 1700001800
}
```

`role_ids` and `dept_id` are empty/null until Plan 4 populates them. They are included now so the JWT shape is stable.

### 3.2 Refresh Token

An opaque UUID stored as the `user_sessions.id` primary key. Not a JWT — no payload to decode. Sent as a signed httpOnly cookie value: `HMAC-SHA256(jti, SECRET_KEY)` so the server can verify it wasn't tampered with before hitting the DB.

## 4. Core Auth Utilities (`app/core/auth.py`)

### 4.1 Password Hashing

```python
hash_password(plain: str) -> str       # Argon2 via passlib CryptContext
verify_password(plain: str, hashed: str) -> bool
```

### 4.2 JWT

```python
@dataclass
class TokenPayload:
    sub: str          # user UUID
    role_ids: list[str]
    dept_id: str | None
    jti: str          # unique token ID
    iat: int
    exp: int

create_access_token(sub: str, role_ids: list[str] = [], dept_id: str | None = None) -> str
decode_access_token(token: str) -> TokenPayload
# Raises ProblemDetails(code="auth.invalid-token", status=401) on failure
```

Signing: `python-jose` with HS256, key = `SECRET_KEY` from config.

### 4.3 `get_current_user` Dependency

```python
async def get_current_user(
    authorization: str = Header(...),
    session: AsyncSession = Depends(get_session),
) -> User:
```

1. Extract Bearer token from `Authorization` header
2. `decode_access_token(token)` → `TokenPayload`
3. Load `User` by `payload.sub` from DB
4. If user not found → `ProblemDetails(code="auth.invalid-token", status=401)`
5. If `user.is_active is False` → `ProblemDetails(code="auth.inactive-user", status=403)`
6. Return user

### 4.4 Refresh Token Denylist (Redis)

```python
async def denylist_token(redis: Redis, jti: str, ttl_seconds: int) -> None:
    # SET deny:<jti> 1 EX <ttl>

async def is_denylisted(redis: Redis, jti: str) -> bool:
    # EXISTS deny:<jti>
```

### 4.5 Login Lockout (Redis)

```python
async def record_failed_login(redis: Redis, email: str) -> None:
    # INCR login:fail:<email>, EXPIRE 900 (15 min)

async def is_locked_out(redis: Redis, email: str) -> bool:
    # GET login:fail:<email> >= 5

async def clear_failed_logins(redis: Redis, email: str) -> None:
    # DEL login:fail:<email>
```

### 4.6 Captcha Hook

```python
async def verify_captcha(token: str | None) -> bool:
    # V1: always returns True
    # V2: verify with hCaptcha/Turnstile provider
    return True
```

## 5. Email Service (`app/core/email.py`)

```python
async def send_email(to: str, subject: str, template: str, context: dict) -> None:
```

- Renders Jinja2 template from `backend/templates/email/<template>.html`
- If `settings.SMTP_HOST` is empty → logs rendered body + subject to stdout (dev fallback)
- If configured → sends via `aiosmtplib` using `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` from config

**Templates:**
- `password_reset.html` — contains the reset link with token, expiry notice

## 6. Auth Module (`app/modules/auth/`)

### 6.1 Schemas (`schemas.py`)

All inherit `BaseSchema` (camelCase serialization).

**Request schemas:**
- `LoginRequest`: `email: str`, `password: str`, `captcha: str | None = None`
- `RefreshRequest`: (no body — cookie only)
- `PasswordChangeRequest`: `current_password: str`, `new_password: str`, `confirm: str` + `mustMatch` x-rule on `new_password`/`confirm`
- `PasswordResetRequestSchema`: `email: str`
- `PasswordResetConfirmSchema`: `token: str`, `new_password: str`, `confirm: str` + `mustMatch` x-rule

**Response schemas:**
- `LoginResponse`: `access_token: str`, `expires_in: int`, `user: UserRead`, `must_change_password: bool`
- `TokenResponse`: `access_token: str`, `expires_in: int`
- `UserRead`: `id: UUID`, `email: str`, `full_name: str`, `department_id: UUID | None`, `is_active: bool`, `must_change_password: bool`, `created_at: datetime`, `updated_at: datetime`
- `SessionRead`: `id: UUID`, `device_label: str | None`, `ip_address: str | None`, `created_at: datetime`, `last_used_at: datetime`, `expires_at: datetime`, `is_current: bool`

**Password validation rule:**
- Min 10 chars, >= 1 letter + >= 1 digit
- Must not equal email or full_name
- Enforced as a custom ajv keyword (`passwordPolicy`) on FE and as a `@field_validator` on BE schemas

### 6.2 Endpoints (`router.py`)

All endpoints declare `public=True` in the permission sense (no `require_perm` until Plan 4). Endpoints that require a logged-in user still use `Depends(get_current_user)` — `public=True` means "no RBAC permission check", not "no authentication".

| Method | Path | Auth | Rate Limit | Returns |
|---|---|---|---|---|
| `POST` | `/auth/login` | public | 20/min per IP | `LoginResponse` + Set-Cookie |
| `POST` | `/auth/refresh` | public (cookie) | — | `TokenResponse` + Set-Cookie |
| `POST` | `/auth/logout` | `get_current_user` | — | 204 |
| `GET` | `/me/profile` | `get_current_user` | — | `UserRead` |
| `PUT` | `/me/password` | `get_current_user` | — | 204 |
| `GET` | `/me/sessions` | `get_current_user` | — | `Page[SessionRead]` |
| `DELETE` | `/me/sessions/{jti}` | `get_current_user` | — | 204 |
| `POST` | `/auth/password-reset/request` | public | 5/min per IP | 200 (always, no enumeration) |
| `POST` | `/auth/password-reset/confirm` | public | — | 204 |

### 6.3 Login Flow

1. Check `is_locked_out(email)` → `ProblemDetails(code="auth.locked-out", status=429)`
2. `verify_captcha(captcha)` → `ProblemDetails(code="auth.captcha-failed", status=400)`
3. Find user by email → generic `ProblemDetails(code="auth.invalid-credentials", status=401)` if not found
4. `verify_password(password, user.password_hash)` → same generic error + `record_failed_login(email)`
5. Check `user.is_active` → same generic error (no info leak)
6. `clear_failed_logins(email)`
7. Create `UserSession` row (jti=new UUID, device_label from User-Agent, ip from request)
8. `create_access_token(sub=user.id, role_ids=[], dept_id=user.department_id)`
9. Return `LoginResponse` + httpOnly cookie with signed refresh token
10. If `user.must_change_password` → `LoginResponse.must_change_password = True`

### 6.4 Refresh Flow

1. Read refresh token from httpOnly cookie → 401 if missing
2. Verify HMAC signature → 401 if tampered
3. Extract jti, check `is_denylisted(jti)` → 401 if revoked
4. Load `UserSession` by jti → 401 if not found
5. Check absolute expiry (`expires_at`) → 401 if expired
6. Check idle expiry (`last_used_at + REFRESH_TOKEN_IDLE_MINUTES`) → 401 if idle too long
7. Denylist old jti (TTL = remaining seconds until `expires_at`)
8. Create new `UserSession` row (new jti, copy device_label/ip, new `last_used_at`)
9. Delete old `UserSession` row
10. Return new access token + new refresh cookie

### 6.5 Logout Flow

1. Read refresh token jti from cookie
2. Denylist it (TTL = remaining seconds until session expires)
3. Delete `UserSession` row
4. Clear cookie
5. Return 204

### 6.6 Password Reset Flow

**Request:**
1. Find user by email — if not found, still return 200 (no enumeration)
2. Generate random token: `secrets.token_urlsafe(32)`
3. Store in Redis: `SET reset:<token> <user_id> EX 3600` (1 hour TTL)
4. Send email with reset link (or log to console in dev)
5. Return 200

**Confirm:**
1. Look up `reset:<token>` in Redis → `ProblemDetails(code="auth.reset-token-invalid", status=400)` if not found/expired
2. Load user by stored user_id
3. Validate new password (password policy)
4. Hash and update `password_hash`, set `must_change_password=False`
5. Delete Redis key
6. Load all `UserSession` rows for this user, denylist each jti in Redis (TTL = remaining seconds until each session's `expires_at`), then delete all rows (force re-login on all devices)
7. Return 204

### 6.7 Password Change Flow

1. Verify `current_password` against `user.password_hash` → `ProblemDetails(code="auth.invalid-credentials", status=401)` if wrong
2. Validate new password (password policy + must not equal email/full_name)
3. Hash and update `password_hash`, set `must_change_password=False`
4. Return 204

### 6.8 Session Management

- `GET /me/sessions` — paginated list of user's sessions via `paginate()`. Each `SessionRead` includes `is_current: bool` (matched by comparing request's refresh jti with session id).
- `DELETE /me/sessions/{jti}` — denylist the token, delete the row. Cannot delete own current session (use logout instead).

## 7. Rate Limiting

- `slowapi` with Redis backend (shared connection)
- `POST /auth/login`: 20 requests/min per IP
- `POST /auth/password-reset/request`: 5 requests/min per IP
- Exceeding limit → 429 response with ProblemDetails shape (`code: "rate-limited"`)
- Rate limiter installed as middleware on the FastAPI app in `main.py`

## 8. Frontend

### 8.1 Auth Library (`src/lib/auth/`)

**`AuthProvider.tsx`:**
- React context wrapping the app
- State: `user: UserRead | null`, `accessToken: string | null`, `isLoading: boolean`
- On mount: attempt silent `POST /auth/refresh` to restore session
  - Success → set user + token in memory, store token in sessionStorage
  - Failure → clear state, remain unauthenticated
- Exposes: `login(email, password, captcha?)`, `logout()`, `isAuthenticated`, `user`, `isLoading`
- `login()` calls `/auth/login`, stores token, sets user
- `logout()` calls `/auth/logout`, clears everything

**`useAuth.ts`:**
- `const { user, isAuthenticated, isLoading, login, logout } = useAuth()`

**`storage.ts`:**
- `getToken(): string | null` — reads from sessionStorage
- `setToken(token: string): void` — writes to sessionStorage
- `clearToken(): void` — removes from sessionStorage
- Never touches localStorage (convention 06)

### 8.2 Axios 401 Interceptor (update `src/api/client.ts`)

1. On 401 response → attempt `POST /auth/refresh` (cookie auto-sent)
2. On refresh success → update in-memory token via AuthProvider, retry original request with new token
3. On refresh failure → `clearToken()`, navigate to `/login`
4. **Request queue:** While a refresh is in-flight, queue concurrent 401'd requests and replay them after the refresh completes. Prevents multiple simultaneous refresh calls.

### 8.3 Pages (`src/modules/auth/`)

| Component | Route | Form Schema | Notes |
|---|---|---|---|
| `LoginPage.tsx` | `/login` | email + password + captcha (optional) | Uses FormRenderer; on success → redirect to `/` or `/password-change` |
| `PasswordResetRequestPage.tsx` | `/password-reset` | email only | Always shows "check your email" message |
| `PasswordResetConfirmPage.tsx` | `/password-reset/confirm` | new password + confirm | Token from URL query param; uses `mustMatch` rule |
| `PasswordChangePage.tsx` | `/password-change` | current + new + confirm | For `must_change_password` flow; uses `mustMatch` + `passwordPolicy` |
| `SessionsPage.tsx` | `/me/sessions` | — (list view) | DataTable with revoke action; highlights current session |

### 8.4 Route Guard

`<RequireAuth>` wrapper component:
- Checks `useAuth().isAuthenticated`
- If `isLoading` → show spinner
- If not authenticated → redirect to `/login`
- If authenticated → render children

This is NOT `<RequirePermission>` (Plan 4). It only checks "is there a valid session."

### 8.5 New Form Rule: `passwordPolicy`

Register on both BE and FE:
- BE: `FormRuleRegistry.register("password_policy", ...)` — validates min 10 chars, >= 1 letter + >= 1 digit
- FE: `registerRuleKeywords(ajv)` adds `passwordPolicy` keyword — same validation logic
- The "must not equal email/full_name" check is BE-only (FE doesn't have those values in the schema context)

## 9. Alembic Migration

Single migration creating both `users` and `user_sessions` tables.

**Seed data** (in same migration via `op.execute`):
- Admin user: `admin@example.com`, password `Admin12345!` (Argon2 hashed), `must_change_password=True`, `is_active=True`
- Makes the system usable on first boot

**`department_id`** is a plain UUID column with no FK constraint. When Plan 4 creates the `departments` table, a separate migration adds the FK.

## 10. Redis Key Namespace

| Key Pattern | Purpose | TTL |
|---|---|---|
| `deny:<jti>` | Refresh token denylist | Remaining seconds until session `expires_at` |
| `login:fail:<email>` | Failed login counter | 900s (15 min) |
| `reset:<token>` | Password reset token → user_id | 3600s (1 hour) |

## 11. Error Codes

All errors use `ProblemDetails` with these stable codes:

| Code | Status | When |
|---|---|---|
| `auth.invalid-credentials` | 401 | Bad email/password (generic, no info leak) |
| `auth.invalid-token` | 401 | Bad/expired access or refresh token |
| `auth.inactive-user` | 403 | User account disabled |
| `auth.locked-out` | 429 | Too many failed login attempts |
| `auth.captcha-failed` | 400 | Captcha verification failed |
| `auth.reset-token-invalid` | 400 | Password reset token expired or not found |
| `auth.password-policy` | 422 | New password doesn't meet policy |
| `auth.cannot-revoke-current` | 400 | Tried to DELETE own current session |
| `rate-limited` | 429 | IP rate limit exceeded |

## 12. Testing Strategy

### 12.1 Backend Unit Tests

- `test_core_auth.py`: hash_password round-trip, verify_password correct/incorrect, create/decode access token, expired token rejection, denylist set/check, lockout counter increment/threshold/clear, captcha hook returns True
- `test_auth_schemas.py`: password policy validation (too short, no digit, no letter, equals email), mustMatch on confirm fields, LoginRequest/LoginResponse serialization

### 12.2 Backend Integration Tests

- `test_auth_endpoints.py`: Full login→refresh→logout cycle, login with bad password (check lockout increments), login when locked out (429), login with inactive user (generic 401), login with must_change_password (flag in response), refresh with valid/expired/denylisted/idle token, password change with correct/incorrect current password, password reset request+confirm cycle, session list + revoke, revoke own session (400), rate limit on login endpoint

### 12.3 Frontend Tests

- `test_auth_provider.tsx`: silent refresh on mount (success/failure), login sets state, logout clears state
- `test_401_interceptor.ts`: auto-refresh on 401, retry queued requests, redirect on refresh failure
- `test_login_page.tsx`: FormRenderer renders, submit calls login, error display, redirect on success
- `test_password_reset.tsx`: request form submit, confirm form with mustMatch validation

### 12.4 Alembic Migration Test

- Verify `upgrade` creates both tables with expected columns
- Verify seed admin user exists and can be loaded
- Verify `downgrade` drops tables cleanly

## 13. Dependencies

All already in `pyproject.toml`:
- `python-jose[cryptography]` — JWT
- `passlib[argon2]` — password hashing
- `redis` — denylist, lockout, rate limiter backend, reset tokens
- `slowapi` — rate limiting
- `aiosmtplib` — email delivery
- `jinja2` — email templates

Frontend additions:
- `react-router-dom` — routing for auth pages + `<RequireAuth>`
- No other new deps expected

## 14. Files Created/Modified

### New files:
- `backend/app/core/auth.py` — password hashing, JWT, get_current_user, denylist, lockout, captcha
- `backend/app/core/email.py` — email service with dev fallback
- `backend/app/modules/auth/__init__.py`
- `backend/app/modules/auth/models.py` — User, UserSession
- `backend/app/modules/auth/schemas.py` — all request/response schemas
- `backend/app/modules/auth/service.py` — login, refresh, logout, password reset, session management
- `backend/app/modules/auth/router.py` — all endpoints
- `backend/app/modules/auth/crud.py` — DB queries (get_user_by_email, create_session, etc.)
- `backend/templates/email/password_reset.html`
- `backend/alembic/versions/xxx_create_users_and_sessions.py`
- `backend/tests/core/test_core_auth.py`
- `backend/tests/modules/auth/test_auth_schemas.py`
- `backend/tests/modules/auth/test_auth_endpoints.py`
- `frontend/src/lib/auth/AuthProvider.tsx`
- `frontend/src/lib/auth/useAuth.ts`
- `frontend/src/lib/auth/storage.ts`
- `frontend/src/lib/auth/index.ts`
- `frontend/src/modules/auth/LoginPage.tsx`
- `frontend/src/modules/auth/PasswordResetRequestPage.tsx`
- `frontend/src/modules/auth/PasswordResetConfirmPage.tsx`
- `frontend/src/modules/auth/PasswordChangePage.tsx`
- `frontend/src/modules/auth/SessionsPage.tsx`
- `frontend/src/modules/auth/components/RequireAuth.tsx`

### Modified files:
- `backend/app/main.py` — register auth router, add slowapi middleware, add Redis connection lifecycle
- `backend/app/api/v1.py` — include auth router (create if not exists)
- `backend/app/core/form_rules.py` — add `password_policy` rule
- `frontend/src/api/client.ts` — add 401 interceptor with refresh + queue
- `frontend/src/lib/form-rules.ts` — add `passwordPolicy` ajv keyword
- `frontend/src/lib/ajv.ts` — (may need update if passwordPolicy registers differently)
- `frontend/src/App.tsx` — wrap in AuthProvider, add routes
