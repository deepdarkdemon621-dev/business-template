# 06 · Auth & Session

## Model: short access JWT + rotating refresh token

| Token | Lifetime | Storage | Sent as |
|---|---|---|---|
| Access JWT | 15–30 min (`ACCESS_TOKEN_TTL_MINUTES`) | Frontend memory (or sessionStorage fallback) | `Authorization: Bearer <t>` header |
| Refresh token | 7 days absolute; 30 min idle (`REFRESH_TOKEN_TTL_DAYS`, `REFRESH_TOKEN_IDLE_MINUTES`) | `httpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` cookie | Cookie (automatic) |

## Flows

### Login

```
POST /api/v1/auth/login { email, password, captcha? }
 → 200 { accessToken, expiresIn, user }
   Set-Cookie: refresh_token=<opaque>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth
```

### Refresh

```
POST /api/v1/auth/refresh   (cookie sent automatically)
 → 200 { accessToken, expiresIn }
   Set-Cookie: refresh_token=<new-opaque>   (OLD is immediately denylisted in Redis)
```

### Logout

```
POST /api/v1/auth/logout
 → 204; denylists current refresh; clears cookie
```

## Access JWT payload

```json
{
  "sub": "<user_uuid>",
  "role_ids": ["<uuid>", ...],
  "dept_id": "<uuid>",
  "jti": "<access_uuid>",
  "iat": 1700000000,
  "exp": 1700001800
}
```

Forbidden: putting additional business fields in the JWT. Keep it minimal.

## Hashing

argon2 via `passlib`. Centralized in `app/core/auth.py`. Business code imports `hash_password` / `verify_password` — never calls `argon2` directly.

## Password policy

- Min 10 chars
- Must contain ≥1 letter and ≥1 digit
- Must not equal the email or full_name
- No complexity bondage beyond that

## Login lockout

- Same account, 5 failures in 15 min → lock 15 min (Redis key `login:fail:<email>`)
- Same IP, 20 requests/min to `/auth/login` → 429 (slowapi + Redis)

## First login

Account created by admin has `must_change_password=True`. On successful login, BE returns a 200 with `user.must_change_password=true` and FE routes to `/password-change` before anything else.

## Password reset

- `POST /auth/password-reset/request { email }` → always 200 (no user enumeration)
- If user exists: generate one-time token, store in Redis with 30 min TTL, email link `https://<host>/password-reset?token=<t>`
- `POST /auth/password-reset/confirm { token, newPassword }` → 204; token consumed immediately

## Endpoints are protected by default

The app factory applies a global `Depends(require_auth)` to all routers. Endpoints that must be public declare `public=True` in their decorator or router-level config. An audit script (below) fails CI if a router function lacks either.

## FE handling

- axios response interceptor is the **only** 401 handler: try `/auth/refresh`; on success retry; on failure clear auth state and `navigate("/login")`
- Business code doesn't write 401 handling

## Sessions UX

- `GET /me/sessions` lists active refresh tokens (device label + last-used + created-at)
- `DELETE /me/sessions/:jti` denylists that specific refresh token

## Captcha

Login and password-reset accept an optional `captcha` field today (V1 stores the hook); V2 wires hCaptcha or Turnstile server verification.

## Mechanical enforcement

- `scripts/audit/audit_permissions.py` — also verifies every router function has either a permission dep OR `public=True` marker
- `scripts/audit/audit_401_handling.ts` — grep: no `catch`/`.then` path in `src/modules/` may match `status === 401`
- secret scanning in CI (gitleaks) to catch accidental `SECRET_KEY` commits
