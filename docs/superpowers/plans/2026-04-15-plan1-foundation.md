# Plan 1: Foundation + Conventions + Auditor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the `business-template` monorepo with a working dev environment (docker-compose up), fully-written convention documentation, CLAUDE.md hierarchy, and an active convention-auditor pipeline (L1 scripts + L2 subagent) — so every subsequent plan writes code against a binding, mechanically-enforced rulebook.

**Architecture:** Monorepo: `backend/` (FastAPI/Python 3.13) + `frontend/` (Vite/React 19/TS) + `docker/` + `docs/` + `scripts/` + `.claude/`. Docker Compose orchestrates Postgres 16, Redis 7, MinIO, ClamAV, backend (uvicorn hot-reload), frontend (vite dev), nginx reverse proxy. All conventions live in `docs/conventions/*.md`, referenced from CLAUDE.md files. `.claude/agents/convention-auditor.md` defines an L2 semantic audit subagent. `scripts/audit/*` implements L1 mechanical checks run in CI.

**Tech Stack:** Python 3.13 + FastAPI + uv + SQLAlchemy 2.0 async + Alembic + PostgreSQL 16 + Redis 7 + MinIO (S3) + ClamAV + Vite + React 19 + TypeScript + Tailwind + shadcn/ui + Docker Compose + Nginx + GitHub Actions.

**Reference spec:** `docs/superpowers/specs/2026-04-15-business-template-core-design.md`

**Project root:** `C:/Programming/business-template` (not yet a git repo — Task 1 initializes it)

---

## File Structure (what this plan creates)

```
business-template/
├── .claude/
│   └── agents/
│       └── convention-auditor.md         ← L2 semantic audit subagent
├── .github/
│   └── workflows/
│       └── ci.yml                         ← lint + test + audit + build
├── .env.example
├── .gitignore
├── README.md
├── backend/
│   ├── CLAUDE.md
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                      ← empty; Plan 3+ adds migrations
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                        ← FastAPI factory + /healthz
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py                  ← Settings (pydantic-settings)
│   │   └── modules/
│   │       └── _template/                 ← copy-source for new modules (empty files with docstrings)
│   ├── pyproject.toml
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── test_healthz.py
├── docker/
│   └── nginx/
│       ├── Dockerfile
│       └── nginx.conf
├── docker-compose.yml
├── docs/
│   ├── conventions/
│   │   ├── 01-schema-validation.md
│   │   ├── 02-service-guards.md
│   │   ├── 03-ui-primitives.md
│   │   ├── 04-forms.md
│   │   ├── 05-api-contract.md
│   │   ├── 06-auth-session.md
│   │   ├── 07-rbac.md
│   │   ├── 08-naming-and-layout.md
│   │   └── 99-anti-laziness.md
│   ├── review-checklist.md
│   └── superpowers/                       ← (already exists: specs/, plans/)
├── frontend/
│   ├── CLAUDE.md
│   ├── Dockerfile
│   ├── components.json                    ← shadcn/ui config
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── router.tsx
│   │   ├── index.css
│   │   ├── vite-env.d.ts
│   │   ├── api/
│   │   │   └── .gitkeep
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   └── CLAUDE.md
│   │   │   ├── form/
│   │   │   │   └── CLAUDE.md
│   │   │   ├── table/.gitkeep
│   │   │   └── layout/.gitkeep
│   │   ├── lib/
│   │   │   ├── design-tokens.ts
│   │   │   └── utils.ts
│   │   └── modules/
│   │       └── .gitkeep
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── vite.config.ts
│   └── vitest.config.ts
├── scripts/
│   └── audit/
│       ├── README.md
│       ├── run_all.sh
│       ├── audit_except.sh
│       ├── audit_todo.sh
│       ├── audit_mock_leak.sh
│       ├── audit_json_schema.sh
│       ├── audit_permissions.py
│       ├── audit_listing.py
│       ├── audit_mui_imports.sh
│       └── audit_pagination_fe.sh
└── CLAUDE.md                              ← root
```

---

## Phase A: Repository init

### Task 1: Initialize git repo and write `.gitignore`

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `.env.example`

- [ ] **Step 1: Init git**

Run:
```bash
cd C:/Programming/business-template
git init -b main
```

Expected: `Initialized empty Git repository in .../business-template/.git/`

- [ ] **Step 2: Write `.gitignore`**

Write to `C:/Programming/business-template/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
.env
.env.local
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
dist/
build/
*.egg-info/

# Node
node_modules/
dist/
.vite/
coverage/
*.tsbuildinfo

# Editors
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# Docker volumes
.docker-data/
postgres-data/
redis-data/
minio-data/

# Project
*.log
.env.*
!.env.example
```

- [ ] **Step 3: Write `README.md`**

Write to `C:/Programming/business-template/README.md`:

```markdown
# business-template

Generalized business back-office template (OA / approval workflow systems).

## Quick start

```bash
cp .env.example .env
docker compose up -d
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8080/api/v1
- MinIO console: http://localhost:9001

## Documentation

- Specs: `docs/superpowers/specs/`
- Implementation plans: `docs/superpowers/plans/`
- Conventions (required reading for any code change): `docs/conventions/`
- Audit agent: `.claude/agents/convention-auditor.md`

## Required reading order (for new contributors / AI agents)

1. `CLAUDE.md` (root)
2. `docs/conventions/08-naming-and-layout.md` — where things live
3. Convention docs relevant to your change area (01–07, 99)
4. Module-local `CLAUDE.md` if any
```

- [ ] **Step 4: Write `.env.example`**

Write to `C:/Programming/business-template/.env.example`:

```bash
# App
APP_ENV=dev
APP_PORT=8080
SECRET_KEY=change-me-dev-only-minimum-32-chars-long

# Database
POSTGRES_DB=business_template
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# S3 / MinIO
S3_ENDPOINT_URL=http://minio:9000
S3_REGION=us-east-1
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=business-template

# ClamAV
CLAMAV_HOST=clamav
CLAMAV_PORT=3310
CLAMAV_ENABLED=true

# Auth
ACCESS_TOKEN_TTL_MINUTES=30
REFRESH_TOKEN_TTL_DAYS=7
REFRESH_TOKEN_IDLE_MINUTES=30

# SMTP (dev: Mailhog or Mailtrap)
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@business-template.local

# CORS
ALLOWED_ORIGINS=http://localhost:8080

# Frontend build-time
VITE_API_BASE_URL=/api/v1
```

- [ ] **Step 5: First commit**

```bash
git add .gitignore README.md .env.example
git commit -m "chore: init repo skeleton"
```

Expected: one commit on `main`.

---

## Phase B: Backend scaffold (FastAPI boots with /healthz)

### Task 2: Create backend project structure

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/_template/__init__.py`
- Create: `backend/app/modules/_template/{models,schemas,service,router,crud}.py`

- [ ] **Step 1: Create directories**

```bash
cd C:/Programming/business-template
mkdir -p backend/app/core backend/app/modules/_template backend/tests backend/alembic/versions
```

- [ ] **Step 2: Write `backend/pyproject.toml`**

```toml
[project]
name = "business-template-backend"
version = "0.1.0"
description = "Generalized business back-office template — backend"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.35",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "python-jose[cryptography]>=3.3",
    "passlib[argon2]>=1.7",
    "python-multipart>=0.0.20",
    "aiosmtplib>=3.0",
    "jinja2>=3.1",
    "redis>=5.2",
    "slowapi>=0.1.9",
    "boto3>=1.35",
    "httpx>=0.28",
    "pillow>=11.0",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-cov>=6.0",
    "ruff>=0.8",
    "mypy>=1.13",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "W", "C4", "SIM", "ASYNC"]
ignore = ["E501"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 3: Write `backend/app/core/config.py`**

```python
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="dev")
    secret_key: str = Field(min_length=32)

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "business_template"

    redis_host: str = "redis"
    redis_port: int = 6379

    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "business-template"

    clamav_host: str = "clamav"
    clamav_port: int = 3310
    clamav_enabled: bool = True

    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7
    refresh_token_idle_minutes: int = 30

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@business-template.local"

    allowed_origins: str = "http://localhost:8080"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="business-template",
        version="0.1.0",
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        openapi_url="/api/openapi.json" if settings.app_env != "prod" else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", tags=["infra"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Create `backend/app/__init__.py` and `backend/app/core/__init__.py`**

Both empty files:

```bash
touch backend/app/__init__.py backend/app/core/__init__.py backend/app/modules/__init__.py
```

- [ ] **Step 6: Create `_template` module skeleton**

Create 5 files under `backend/app/modules/_template/` — each a stub referencing conventions:

`backend/app/modules/_template/__init__.py`:
```python
"""Copy-source for new business modules.

Copy this directory to `backend/app/modules/<feature>/`, rename internals, and fill in.
See docs/conventions/08-naming-and-layout.md for the feature-first layout rules.
"""
```

`backend/app/modules/_template/models.py`:
```python
"""SQLAlchemy ORM models for this module.

Rules:
- Use Mapped[] / mapped_column() (SQLAlchemy 2.0 style).
- Inherit from app.core.database.Base (added in Plan 2).
- Declare __guards__ for delete / state transitions (see 02-service-guards).
"""
```

`backend/app/modules/_template/schemas.py`:
```python
"""Pydantic request/response schemas.

Rules (see 01-schema-validation + 05-api-contract):
- Use Field(max_length=..., ge=..., pattern=...) for field-level rules.
- Use `json_schema_extra={"x-rules": [...]}` for cross-field (FormRuleRegistry).
- Response schemas MUST strip sensitive fields (no password_hash, no raw tokens).
- alias_generator=to_camel + populate_by_name=True on model_config.
"""
```

`backend/app/modules/_template/service.py`:
```python
"""Business logic layer.

Rules:
- All write ops via service, not directly from router.
- Service methods run inside `async with session.begin()` (one transaction per call).
- Run __guards__ before mutations (see 02-service-guards).
- Emit audit events for every mutation (handled by service base in Plan 2).
"""
```

`backend/app/modules/_template/router.py`:
```python
"""FastAPI routes for this module.

Rules (see 05-api-contract + 06-auth-session + 07-rbac):
- Every endpoint declares permission via Depends(require_perm("...")), OR public=True.
- List endpoints inherit PaginatedEndpoint; NEVER return bare arrays.
- Use apply_scope() for data-scoped queries.
- Errors as Problem Details (app.core.errors).
"""
```

`backend/app/modules/_template/crud.py`:
```python
"""Data access helpers (pure DB queries).

Rules:
- Never call .all() bare — use paginate() for list, .scalar_one() for single.
- Must take AsyncSession as an argument; never create one.
"""
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with /healthz and module template"
```

### Task 3: Write FastAPI health check test

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_healthz.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/__init__.py` — empty file.

`backend/tests/conftest.py`:

```python
import os

# Ensure tests use a predictable SECRET_KEY (min 32 chars required by Settings)
os.environ.setdefault("SECRET_KEY", "x" * 40)
os.environ.setdefault("APP_ENV", "test")

import pytest
from fastapi.testclient import TestClient

from app.main import app as _app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app)
```

`backend/tests/test_healthz.py`:

```python
def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Install deps and run**

```bash
cd backend
uv sync
uv run pytest tests/test_healthz.py -v
```

Expected: `test_healthz_returns_ok PASSED`

- [ ] **Step 3: Commit**

```bash
cd ..
git add backend/tests backend/uv.lock
git commit -m "test(backend): health check smoke test passes"
```

### Task 4: Initialize Alembic

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`

- [ ] **Step 1: Generate alembic scaffold**

```bash
cd backend
uv run alembic init -t async alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Rewrite `backend/alembic.ini`** (keep only essential, remove logging noise)

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]
hooks = ruff
ruff.type = console_scripts
ruff.entrypoint = ruff
ruff.options = format REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 3: Rewrite `backend/alembic/env.py`** to read DSN from Settings:

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.postgres_dsn)

# target_metadata wired in Plan 2 when Base is introduced
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Commit**

```bash
cd ..
git add backend/alembic.ini backend/alembic/
git commit -m "chore(backend): scaffold alembic (async) with DSN from settings"
```

---

## Phase C: Frontend scaffold (Vite boots, Tailwind works)

### Task 5: Initialize Vite + React + TypeScript + Tailwind

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/{main.tsx,App.tsx,router.tsx,index.css,vite-env.d.ts}`
- Create: `frontend/src/lib/{design-tokens.ts,utils.ts}`
- Create: `frontend/components.json`

- [ ] **Step 1: Create directories**

```bash
cd C:/Programming/business-template
mkdir -p frontend/src/{api,components/ui,components/form,components/table,components/layout,lib,modules,types}
touch frontend/src/api/.gitkeep frontend/src/components/table/.gitkeep frontend/src/components/layout/.gitkeep frontend/src/modules/.gitkeep frontend/src/types/.gitkeep
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "business-template-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint src --max-warnings 0",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc -b --noEmit"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.0",
    "react-hook-form": "^7.54.0",
    "ajv": "^8.17.0",
    "ajv-formats": "^3.0.1",
    "axios": "^1.7.9",
    "clsx": "^2.1.1",
    "class-variance-authority": "^0.7.1",
    "tailwind-merge": "^2.6.0",
    "lucide-react": "^0.468.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.7.2",
    "vite": "^6.0.0",
    "tailwindcss": "^3.4.17",
    "postcss": "^8.5.0",
    "autoprefixer": "^10.4.20",
    "vitest": "^2.1.8",
    "@testing-library/react": "^16.1.0",
    "@testing-library/jest-dom": "^6.6.3",
    "jsdom": "^25.0.1",
    "eslint": "^9.17.0",
    "@eslint/js": "^9.17.0",
    "typescript-eslint": "^8.18.0"
  }
}
```

- [ ] **Step 3: Write `frontend/vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    watch: { usePolling: true }, // for docker-compose volume mounts on Windows/WSL
  },
});
```

- [ ] **Step 4: Write `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

- [ ] **Step 5: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": false,
    "allowSyntheticDefaultImports": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 6: Write `frontend/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "composite": true,
    "strict": true,
    "skipLibCheck": true
  },
  "include": ["vite.config.ts", "vitest.config.ts"]
}
```

- [ ] **Step 7: Write `frontend/src/lib/design-tokens.ts` (SSOT for both Tailwind + runtime)**

```ts
/**
 * Design tokens — single source of truth.
 *
 * Both tailwind.config.ts and runtime components (MUI-less shadcn/ui setup)
 * MUST read from this file. Never hard-code colors / spacing / radii elsewhere.
 *
 * See docs/conventions/03-ui-primitives.md.
 */

export const tokens = {
  colors: {
    // Neutrals
    background: "hsl(0 0% 100%)",
    foreground: "hsl(240 10% 3.9%)",
    muted: "hsl(240 4.8% 95.9%)",
    mutedForeground: "hsl(240 3.8% 46.1%)",
    border: "hsl(240 5.9% 90%)",
    input: "hsl(240 5.9% 90%)",

    // Brand
    primary: "hsl(221.2 83% 53.3%)",
    primaryForeground: "hsl(210 40% 98%)",

    // Semantic
    destructive: "hsl(0 72.2% 50.6%)",
    destructiveForeground: "hsl(0 0% 98%)",
    success: "hsl(142.1 76.2% 36.3%)",
    successForeground: "hsl(0 0% 98%)",
    warning: "hsl(38 92% 50%)",
    warningForeground: "hsl(0 0% 98%)",
  },
  radius: {
    sm: "0.25rem",
    md: "0.5rem",
    lg: "0.75rem",
  },
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    base: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
  },
} as const;

export type DesignTokens = typeof tokens;
```

- [ ] **Step 8: Write `frontend/tailwind.config.ts`** — reads tokens

```ts
import type { Config } from "tailwindcss";
import { tokens } from "./src/lib/design-tokens";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: tokens.colors.background,
        foreground: tokens.colors.foreground,
        muted: {
          DEFAULT: tokens.colors.muted,
          foreground: tokens.colors.mutedForeground,
        },
        border: tokens.colors.border,
        input: tokens.colors.input,
        primary: {
          DEFAULT: tokens.colors.primary,
          foreground: tokens.colors.primaryForeground,
        },
        destructive: {
          DEFAULT: tokens.colors.destructive,
          foreground: tokens.colors.destructiveForeground,
        },
        success: {
          DEFAULT: tokens.colors.success,
          foreground: tokens.colors.successForeground,
        },
        warning: {
          DEFAULT: tokens.colors.warning,
          foreground: tokens.colors.warningForeground,
        },
      },
      borderRadius: tokens.radius,
      fontSize: tokens.fontSize,
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 9: Write `frontend/postcss.config.js`**

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 10: Write `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>business-template</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 11: Write `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
```

- [ ] **Step 12: Write `frontend/src/main.tsx`**

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
```

- [ ] **Step 13: Write `frontend/src/App.tsx`**

```tsx
export default function App() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-semibold">business-template</h1>
        <p className="text-sm text-muted-foreground">foundation ready.</p>
      </div>
    </main>
  );
}
```

- [ ] **Step 14: Write `frontend/src/router.tsx`**

```tsx
import { createBrowserRouter } from "react-router-dom";
import App from "./App";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
  },
]);
```

- [ ] **Step 15: Write `frontend/src/lib/utils.ts`**

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 16: Write `frontend/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />
```

- [ ] **Step 17: Write `frontend/src/test-setup.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 18: Write `frontend/components.json` (shadcn/ui config, we'll add components in Plan 2)**

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/index.css",
    "baseColor": "neutral",
    "cssVariables": false,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/lib/hooks"
  },
  "iconLibrary": "lucide"
}
```

- [ ] **Step 19: Install and verify**

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

Expected: build succeeds, `dist/` created.

- [ ] **Step 20: Commit**

```bash
cd ..
git add frontend/ -f
git commit -m "feat(frontend): scaffold Vite+React+TS+Tailwind with design tokens"
```

### Task 6: Write a smoke test for the frontend

**Files:**
- Create: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /business-template/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test**

```bash
cd frontend
npm test
```

Expected: `1 passed`.

- [ ] **Step 3: Commit**

```bash
cd ..
git add frontend/src/App.test.tsx
git commit -m "test(frontend): smoke test App renders"
```

---

## Phase D: Docker dev environment

### Task 7: Write backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project || uv sync

COPY . .

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore(backend): add Dockerfile (dev)"
```

### Task 8: Write frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`

- [ ] **Step 1: Write `frontend/Dockerfile`**

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

- [ ] **Step 2: Commit**

```bash
git add frontend/Dockerfile
git commit -m "chore(frontend): add Dockerfile (dev)"
```

### Task 9: Write nginx reverse proxy (dev)

**Files:**
- Create: `docker/nginx/Dockerfile`
- Create: `docker/nginx/nginx.conf`

- [ ] **Step 1: Create nginx dir**

```bash
mkdir -p docker/nginx
```

- [ ] **Step 2: Write `docker/nginx/nginx.conf`**

```nginx
worker_processes 1;

events { worker_connections 1024; }

http {
    include mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    # Dev: proxy /api to FastAPI, everything else to Vite dev server
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:5173;
    }

    server {
        listen 80;
        server_name _;
        client_max_body_size 50M;

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /healthz {
            proxy_pass http://backend;
        }

        # Vite HMR websocket
        location /@vite/ {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

- [ ] **Step 3: Write `docker/nginx/Dockerfile`**

```dockerfile
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
```

- [ ] **Step 4: Commit**

```bash
git add docker/nginx
git commit -m "chore(docker): add nginx reverse proxy (dev)"
```

### Task 10: Write docker-compose.yml (dev)

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-business_template}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-minioadmin}
    ports:
      - "9001:9001"
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  clamav:
    image: clamav/clamav:stable
    volumes:
      - clamav-data:/var/lib/clamav
    healthcheck:
      test: ["CMD", "clamdcheck.sh"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s

  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - "8025:8025"  # web UI

  backend:
    build: ./backend
    env_file: .env
    environment:
      POSTGRES_HOST: db
      REDIS_HOST: redis
      S3_ENDPOINT_URL: http://minio:9000
      CLAMAV_HOST: clamav
      SMTP_HOST: mailhog
    volumes:
      - ./backend:/app
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      timeout: 5s
      retries: 10

  frontend:
    build: ./frontend
    env_file: .env
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

  nginx:
    build: ./docker/nginx
    ports:
      - "${APP_PORT:-8080}:80"
    depends_on:
      - backend
      - frontend

volumes:
  postgres-data:
  redis-data:
  minio-data:
  clamav-data:
```

- [ ] **Step 2: Start the stack**

```bash
cp .env.example .env
docker compose up -d --build
```

- [ ] **Step 3: Verify all services healthy**

```bash
docker compose ps
```

Expected: all services `running` / `healthy` (ClamAV may take 2 min on first start to download sigs).

- [ ] **Step 4: Hit healthz through nginx**

```bash
curl http://localhost:8080/healthz
```

Expected: `{"status":"ok"}`

- [ ] **Step 5: Open frontend in browser**

Visit `http://localhost:8080` → page shows "business-template" heading.

- [ ] **Step 6: Stop stack and commit**

```bash
docker compose down
git add docker-compose.yml
git commit -m "chore(docker): add dev docker-compose with all services"
```

---

## Phase E: Conventions documentation

Each task below writes one convention doc. Engineer-facing requirement: **every doc ends with a "Mechanical enforcement" section listing the audit scripts that enforce it**.

### Task 11: Write `docs/conventions/01-schema-validation.md`

**Files:**
- Create: `docs/conventions/01-schema-validation.md`

- [ ] **Step 1: Create directory**

```bash
mkdir -p docs/conventions
```

- [ ] **Step 2: Write file**

````markdown
# 01 · Schema / Validation Contract

## Rule

> **Pydantic is the only authoring format for validation.**
> **JSON Schema is the transport format between BE and FE.**
> **Nobody hand-writes JSON Schema files.**

## Why

A single source of truth eliminates FE/BE validation drift. Pydantic gives Python type safety, IDE completion, and refactor safety. JSON Schema gives FE a runtime-loadable schema for both static and dynamic (future form engine) forms.

## How

### Static forms (developers write Pydantic)

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Literal

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(max_length=120)
    role: Literal["admin", "member"]
    age: int = Field(ge=18, le=120)
    phone: str = Field(pattern=r"^\+?[0-9\s\-()]{7,20}$")
```

FastAPI auto-exports this to OpenAPI/JSON Schema. FE consumes via `openapi-typescript` (→ TS types) and via ajv (→ runtime validation in forms).

### Dynamic forms (V2 form engine)

Admin UI writes config → `form_engine.compile(config)` → JSON Schema → same FE renderer, same ajv instance. Backend uses `pydantic.create_model(..., **fields)` to dynamically construct a Pydantic class for validation.

## Cross-field rules: FormRuleRegistry

Pydantic's `@model_validator` does not auto-export to JSON Schema. For cross-field rules we use a **shared rule vocabulary** implemented on both sides:

| Rule | Arguments | Meaning |
|---|---|---|
| `dateOrder` | `{ start, end }` | `end >= start` |
| `mustMatch` | `{ a, b }` | `a == b` (password confirm, etc.) |
| `conditionalRequired` | `{ when: {field, equals}, then: [fields] }` | If `when` condition true, `then` fields required |
| `mutuallyExclusive` | `{ fields: [...] }` | At most one filled |
| `uniqueInList` | `{ path, key }` | List at `path`, each item's `key` unique |

Attach via `json_schema_extra`:

```python
class ApplicationCreate(BaseModel):
    start_date: date
    end_date: date
    model_config = {
        "json_schema_extra": {
            "x-rules": [
                {"type": "dateOrder", "start": "start_date", "end": "end_date"}
            ]
        }
    }
```

The same declaration drives an auto-generated `@model_validator` on the BE side (from the registry) AND is consumed by ajv on the FE.

## Boundaries

**Allowed:** any rule present in FormRuleRegistry.
**Not allowed:** free-form Python lambdas / inline `@model_validator` for cross-field logic when an equivalent vocabulary rule would fit.
**Escape hatch:** if the rule truly can't be expressed in the vocabulary, add a new entry to the registry with both BE + FE implementations before using it. Document the addition in a PR.

## Mechanical enforcement

- `scripts/audit/audit_json_schema.sh` — fails if any `*.schema.json` appears under `backend/` or `frontend/src/` (excluding `frontend/src/api/generated/`)
- `scripts/audit/audit_listing.py` — reviews endpoint signatures for missing Pydantic response_model
- CI step: run `pytest` against `tests/contracts/` (to be added in Plan 2) that round-trips Pydantic → JSON Schema → ajv-validates known samples
````

- [ ] **Step 3: Commit**

```bash
git add docs/conventions/01-schema-validation.md
git commit -m "docs(conventions): 01 schema validation"
```

### Task 12: Write `docs/conventions/02-service-guards.md`

**Files:**
- Create: `docs/conventions/02-service-guards.md`

- [ ] **Step 1: Write file**

````markdown
# 02 · Service Guards (Business Invariants)

## Rule

> **All pre-mutation business invariants live in a guard registry, not inline in endpoints.**

## Why

Without a vocabulary, every developer (and AI) writes ad-hoc `if exists(...): raise` checks. Same invariant gets re-invented in slightly different ways; rules drift; error codes differ; FE can't render consistent messages.

## Vocabulary (ServiceGuardRegistry)

| Guard | Arguments | Meaning |
|---|---|---|
| `NoDependents` | `(table, fk_col)` | Forbid delete if rows exist in `table` where `fk_col == self.id` |
| `NoActiveChildren` | `(relation)` | Forbid op if any related row has `is_active=True` |
| `StateAllows` | `(field, allowed=[...])` | Forbid op unless `self.<field>` in `allowed` |
| `ImmutableAfter` | `(field, frozen_from=...)` | Forbid update when `self.<field>` has reached the frozen state |
| `SameDepartment` | — | Target must share `department_id` with actor |

## Declarative usage

```python
class Department(Base):
    __guards__ = {
        "delete": [
            NoDependents("users", "department_id"),
            NoDependents("roles", "default_department_id"),
        ],
    }
```

Service base class (Plan 2) runs `__guards__` for the matching operation before executing the mutation. On failure, raises `GuardViolationError(code="no_dependents", ctx={"table": "users", "count": 12})`.

## FE deletability query

Every guarded resource exposes `GET /{resource}/{id}/deletable`:

```json
{
  "can": false,
  "reason_code": "no_dependents",
  "details": { "table": "users", "count": 12 }
}
```

FE uses this to disable destructive buttons with an explanatory tooltip, not let the user click and get a 409.

## Defense in depth

- DB FK constraints use `ON DELETE RESTRICT` — ultimate backstop
- Service-layer guards — primary UX layer
- FE `deletable?` query — best UX

## Boundaries

**Allowed:** guards in registry, `__guards__` declaration on models.
**Not allowed:** `if <check>: raise HTTPException(...)` inside endpoints for pre-mutation business checks.
**Escape hatch:** add new guard type to registry with tests. Don't add it inline.

## Mechanical enforcement

- `scripts/audit/audit_guards.py` (added in Plan 2) — AST scan: every model with `delete` route must have `__guards__` declared OR be explicitly tagged `__no_guards__ = True` with a comment justification
- CI test: every `GuardViolationError.code` must appear in the registry keys set
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/02-service-guards.md
git commit -m "docs(conventions): 02 service guards"
```

### Task 13: Write `docs/conventions/03-ui-primitives.md`

**Files:**
- Create: `docs/conventions/03-ui-primitives.md`

- [ ] **Step 1: Write file**

````markdown
# 03 · UI Primitives (shadcn/ui + Tailwind)

## Rule

> **One design-token source. Variants defined once via `cva`. Business pages may only import from `@/components/ui`, `@/components/form`, `@/components/table`, `@/components/layout`.**

## Why

Tailwind alone enables drift — each page uses different `p-4 / py-3 px-5`, different shadows, different radii. Without a primitive layer, AI re-invents button/input styles in every module.

## Layering

```
Design tokens (src/lib/design-tokens.ts)
      │
      ▼
Tailwind config (reads tokens; never hard-codes hex)
      │
      ▼
shadcn/ui primitives (@/components/ui) — Radix + Tailwind + cva
      │
      ▼
Business pages (@/modules/*) — compose primitives, no raw CSS
```

## Do

- Import only from the facade dirs listed in the Rule.
- Extend `@/components/ui/Button.tsx` by adding a new cva variant, NOT by adding className overrides at call sites.
- Use Tailwind utilities only for **layout / spacing / flex / grid** in page composition.

## Don't

- Import `@radix-ui/*` directly in a page.
- Pass className overriding internal Button styles (`<Button className="bg-red-500">` ❌).
- Add new colors / radii / font sizes anywhere except `src/lib/design-tokens.ts`.
- Copy a shadcn/ui component into `@/modules/...` — always into `@/components/ui/`.

## Mechanical enforcement

- `scripts/audit/audit_mui_imports.sh` — also scans for `@radix-ui/*` imports outside `src/components/ui/`
- eslint rule (Plan 2): forbid className on components from `@/components/ui` beyond a small allowlist (`w-*`, `h-*`, positioning classes)
- CI: `tailwind.config.ts` must reference `tokens` export from `design-tokens.ts` (audit script)
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/03-ui-primitives.md
git commit -m "docs(conventions): 03 UI primitives"
```

### Task 14: Write `docs/conventions/04-forms.md`

**Files:**
- Create: `docs/conventions/04-forms.md`

- [ ] **Step 1: Write file**

````markdown
# 04 · Forms (RHF + ajv + JSON Schema)

## Rule

> **One form pipeline for the entire app: JSON Schema → RHF `useForm` with ajv resolver → `<FormRenderer>` → submit.**

## Why

Any deviation fragments the validation story (01-schema-validation) and the UI layer (03-ui-primitives). One pipeline = AI has one pattern to follow = no drift.

## Pipeline

```
API endpoint (FastAPI) ──▶ OpenAPI / JSON Schema
                                     │
                        static schema │ or   dynamic schema (form engine, V2)
                                     ▼
                        fetch() as JSON Schema
                                     │
                                     ▼
             useForm({ resolver: ajvResolver(schema, { customRules }) })
                                     │
                                     ▼
                          <FormRenderer schema={schema} />
                                     │
                                     ▼
                      recurse into Field components
                           (fields live in @/components/form/fields/)
                                     │
                                     ▼
                                 handleSubmit
```

## Components

- `@/components/form/FormRenderer.tsx` — recursive renderer reading JSON Schema and `x-rules`
- `@/components/form/fields/String.tsx` / `Number.tsx` / `Boolean.tsx` / `Date.tsx` / `Enum.tsx` / `File.tsx` / `Array.tsx` / `Object.tsx` — one per JSON Schema type
- `FieldRegistry` — maps `x-widget` hints to custom fields (e.g. `x-widget: "rich-text"` → rich text editor)
- `@/lib/ajv.ts` — singleton ajv instance with `ajv-formats` + all FormRuleRegistry rules registered

## Do

- Build all forms via `<FormRenderer schema={...} />`.
- Extend by registering new field widgets in `FieldRegistry`.
- Include cross-field rules via `json_schema_extra={"x-rules": [...]}` on the Pydantic model (see 01).

## Don't

- Hand-write `<input>`, `<Input>`, `<TextField>` inside a business page.
- Replace ajv with Zod, Yup, or custom validators.
- Inline `@model_validator` cross-field rules that bypass FormRuleRegistry.

## Mechanical enforcement

- `scripts/audit/audit_forms_fe.ts` (Plan 2) — scans `src/modules/**/*.tsx` for direct `<Input|<TextField|<Field` usages outside `@/components/form/`
- contract test: every x-rule type seen in generated OpenAPI must be registered in `@/lib/ajv.ts`
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/04-forms.md
git commit -m "docs(conventions): 04 forms"
```

### Task 15: Write `docs/conventions/05-api-contract.md`

**Files:**
- Create: `docs/conventions/05-api-contract.md`

- [ ] **Step 1: Write file**

````markdown
# 05 · API Contract

## Errors: RFC 7807 Problem Details (extended)

All error responses:

```json
{
  "type": "about:blank",
  "title": "Guard violation",
  "status": 409,
  "detail": "Department has 12 users; cannot delete",
  "code": "no_dependents",
  "errors": [],
  "guard_violation": { "table": "users", "count": 12 }
}
```

| Field | Meaning |
|---|---|
| `type` | URI identifying the problem type (spec uses `about:blank` for common cases) |
| `title` | Short human summary |
| `status` | HTTP status (matches response code) |
| `detail` | Request-specific message |
| `code` | Machine-readable error code (stable across versions) — **use this for FE logic** |
| `errors` | Per-field validation errors `[{field, code, message}]` (for 422) |
| `guard_violation` | Present when a guard triggered; see 02 |

## Pagination

List endpoints:

- **Request:** `?page=1&size=20` (1-based page; `size` capped at 100 server-side)
- **Response shape:**
  ```json
  {
    "items": [...],
    "total": 1234,
    "page": 1,
    "size": 20,
    "hasNext": true
  }
  ```
- Bare arrays are **forbidden** in list responses.
- The `size` param is clamped server-side; client can't exceed 100 even if they request it.

## Response envelope

No outer envelope (no `{code, data, message}` wrapper). Successful responses are the resource itself or the pagination struct above. Errors go through Problem Details. HTTP status codes are authoritative.

## Naming boundary

- Backend (Python / DB / Pydantic internals): `snake_case`
- Wire format (JSON over HTTP): `camelCase`
- Transition: all Pydantic response models set `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)` in a shared base class

## List filter / sort / search

- **Filter:** `?status=approved&department_id=3` — query keys match whitelisted fields
- **Sort:** `?sort=-created_at,name` — comma-separated; `-` prefix = descending
- **Search:** `?q=keyword` — backend decides which fields to match
- Unknown filter keys → 400 Problem Details

## Export

For "give me everything" needs, use a dedicated export endpoint:

- `GET /{resource}/export?format=csv` — streams CSV (or xlsx in V2)
- **Not** the list endpoint with `size=huge`

## Versioning

All routes prefixed `/api/v1/...`. Breaking changes → `v2` parallel routes.

## Mechanical enforcement

- `scripts/audit/audit_listing.py` — AST-scans list endpoints; fails if return type is not `Page[X]` (Plan 2 adds `Page` generic)
- `scripts/audit/audit_error_shape.py` (Plan 2) — every `raise HTTPException` must carry a `code`; bare raises fail
- CI: OpenAPI → TS codegen must produce no conflicts with existing `src/api/generated/` before merge
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/05-api-contract.md
git commit -m "docs(conventions): 05 API contract"
```

### Task 16: Write `docs/conventions/06-auth-session.md`

**Files:**
- Create: `docs/conventions/06-auth-session.md`

- [ ] **Step 1: Write file**

````markdown
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
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/06-auth-session.md
git commit -m "docs(conventions): 06 auth and session"
```

### Task 17: Write `docs/conventions/07-rbac.md`

**Files:**
- Create: `docs/conventions/07-rbac.md`

- [ ] **Step 1: Write file**

````markdown
# 07 · RBAC (Role + Permission + Scope)

## Tables

```
departments        (id, name, parent_id, path)     -- materialized path
permissions        (id, code, description)          -- code = "resource:action"
roles              (id, code, name, is_system)
role_permissions   (role_id, permission_id, scope)  -- scope ∈ {global, dept_tree, dept, own}
user_roles         (user_id, role_id)               -- many-to-many
users              (id, email, department_id, is_superadmin)
```

## Permission code format

`resource:action`, lowercase, hyphen-separated resource names.

**Allowed actions (fixed vocabulary):**
`create`, `read`, `update`, `delete`, `list`, `export`, `approve`, `reject`, `publish`, `invoke`

Examples: `user:create`, `department:delete`, `form-template:publish`, `ai-analysis:invoke`.

Extending the action vocabulary requires a PR review. Don't invent `yeet` or `nuke`.

## Scope semantics

| Scope | Row visibility |
|---|---|
| `global` | All rows in the system |
| `dept_tree` | Actor's department + all descendants (materialized path `LIKE '<actor_dept_path>%'`) |
| `dept` | Actor's department only |
| `own` | Rows where `created_by == actor.id` |

`is_superadmin=True` bypasses all permission checks. Only the built-in superadmin role grants this. No self-service way to set it.

## Declarative checks (endpoints)

```python
@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_perm("user:delete"))],
)
async def delete_user(
    user_id: UUID,
    target: User = Depends(load_in_scope("user:delete", get_user)),
    service: UserService = Depends(),
):
    await service.delete(target)
```

- `require_perm` → 403 if user lacks the permission in any scope
- `load_in_scope` → 404 if the target isn't visible in the user's scope for this permission

## Declarative checks (list queries)

```python
stmt = apply_scope(select(User), current_user, "user:list", dept_field="department_id")
```

Never write `select(User).where(...)` directly on a protected resource without `apply_scope`. The audit scanner flags this.

## Seed

- `app/core/permissions.py` defines permission codes as constants. At app startup, the list is **upserted** into the DB: new codes inserted, removed codes logged as `WARN` (not deleted, to preserve role_permissions history)
- Built-in roles (`superadmin`, `admin`, `member`) seeded via Alembic data migration

## FE surface

- `GET /me/permissions` returns `[{ code, scope }]`
- `usePermissions().can("user:delete")` → boolean (UI only; BE is source of truth)
- FE rendering: hide/disable buttons based on permissions; NEVER block BE work on this

## Mechanical enforcement

- `scripts/audit/audit_permissions.py` — AST-scan every FastAPI route for `require_perm` or `public=True`
- `scripts/audit/audit_scope.py` (Plan 2) — grep `select(` on models declared as "scoped" (metadata) without `apply_scope`
- CI test: every permission code referenced in code must exist in `app/core/permissions.py`
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/07-rbac.md
git commit -m "docs(conventions): 07 RBAC"
```

### Task 18: Write `docs/conventions/08-naming-and-layout.md`

**Files:**
- Create: `docs/conventions/08-naming-and-layout.md`

- [ ] **Step 1: Write file**

````markdown
# 08 · Naming & Layout

## Monorepo structure

```
business-template/
├── backend/                 FastAPI service
├── frontend/                Vite SPA
├── docker/                  Dockerfiles & nginx config
├── docs/                    specs, plans, conventions
├── scripts/audit/           L1 audit scripts
├── .claude/agents/          L2 audit subagent
├── .github/workflows/       CI
└── docker-compose.yml       dev orchestration
```

## Backend: feature-first

```
backend/app/
├── main.py
├── core/                    infra: config, auth, guards, form_rules, pagination, ...
└── modules/
    ├── _template/           copy-source for new modules
    ├── auth/
    ├── user/
    ├── department/
    └── <feature>/
        ├── models.py        SQLAlchemy ORM
        ├── schemas.py       Pydantic IO
        ├── service.py       business logic
        ├── router.py        FastAPI endpoints
        └── crud.py          query helpers
```

**Rule:** one feature = one module directory. New feature → copy `_template/` to `modules/<name>/`.

**Rule:** `app/api/v1.py` only aggregates routers. No business code there.

## Frontend: feature-first, mirrors backend

```
frontend/src/
├── App.tsx, main.tsx, router.tsx
├── api/
│   ├── client.ts            axios + interceptors (Plan 3)
│   └── generated/           openapi-typescript output — DO NOT EDIT
├── lib/
│   ├── design-tokens.ts     SSOT for colors/spacing/radii (read by tailwind.config.ts)
│   ├── ajv.ts               ajv instance + rule registrations (Plan 2)
│   ├── auth/                AuthProvider, useAuth, usePermissions (Plan 3)
│   └── utils.ts
├── components/
│   ├── ui/                  shadcn/ui facade (ONLY import source for primitives)
│   ├── form/                FormRenderer, Field, FieldRegistry
│   ├── table/               DataTable (server pagination only)
│   └── layout/              AppShell, Sidebar, TopBar
└── modules/
    ├── auth/
    ├── user/
    └── <feature>/           pages + module-local components + hooks
```

**Rule:** frontend `modules/<feature>/` names match backend `modules/<feature>/`. One-to-one.

## Naming

| Context | Convention | Example |
|---|---|---|
| Python modules, files | snake_case | `audit_log.py` |
| Python classes | PascalCase | `AuditLog` |
| Python funcs/vars | snake_case | `get_user_by_id` |
| TypeScript files (component) | PascalCase | `UserTable.tsx` |
| TypeScript files (hook/util) | camelCase | `useAuth.ts`, `formatDate.ts` |
| TypeScript vars/funcs | camelCase | `currentUser` |
| TypeScript types/interfaces | PascalCase | `UserRow` |
| URLs (routes) | kebab-case, plural nouns | `/api/v1/audit-logs` |
| JSON fields (wire) | camelCase | `{ createdAt, fullName }` |
| DB columns | snake_case | `created_at`, `full_name` |
| Permission codes | `resource:action` | `audit-log:list` |
| CSS class extension | Tailwind utility | `flex gap-4 p-4` |

## CLAUDE.md hierarchy

1. `CLAUDE.md` (root) — entry, required-reading index
2. `backend/CLAUDE.md`, `frontend/CLAUDE.md` — layer rules
3. `app/core/CLAUDE.md`, `components/ui/CLAUDE.md`, `components/form/CLAUDE.md` — local constraints

CLAUDE.md files are **short** (≤200 lines). They reference `docs/conventions/*` for detail. Never duplicate convention content.

## Mechanical enforcement

- `scripts/audit/audit_layout.py` (Plan 2) — reject modules that skip any of the 5 standard file names
- CI: new modules must include the 5 canonical files (even if stub)
````

- [ ] **Step 2: Commit**

```bash
git add docs/conventions/08-naming-and-layout.md
git commit -m "docs(conventions): 08 naming and layout"
```

### Task 19: Write `docs/conventions/99-anti-laziness.md`

**Files:**
- Create: `docs/conventions/99-anti-laziness.md`

- [ ] **Step 1: Write file**

````markdown
# 99 · Anti-laziness Checklist

Living document. When a new AI-laziness pattern is observed, add a row here with both symptom and mechanical interception.

| # | Pattern | Symptom | Interception |
|---|---|---|---|
| 1 | **FE-side pagination** | `.slice(start, end)` in a page component | `<DataTable>` accepts no `paginationMode` toggle (server-only); list API never returns bare arrays. `audit_pagination_fe.sh`. |
| 2 | **FE-side filter/search** | Full fetch + `.filter()` / `.includes()` | Same as 1 + BE supports `?q=` / field filters. `audit_listing.py` flags endpoints returning all rows. |
| 3 | **N+1 query** | `for obj in list: obj.related` | Require `selectinload` / `joinedload` on relations used in list endpoints; slow-query log in dev; `audit_n_plus_one.py` (Plan 5). |
| 4 | **Missing index** | New filter column has no index | Alembic migration review checklist (PR template) + `audit_migration.py` (Plan 3). |
| 5 | **Swallowed exception** | `except: pass` or `except Exception: pass` | `audit_except.sh` — CI fails. |
| 6 | **Hardcoded magic value** | `if role == "admin":` in code | Use `Role.ADMIN` enum; `audit_magic_strings.py` (Plan 3). |
| 7 | **Missing transaction** | Multiple writes without `async with session.begin()` | Service base class enforces wrapper (Plan 2). |
| 8 | **Unauthorized endpoint** | New router fn with no `require_perm` / `public=True` | `audit_permissions.py` — CI fails. |
| 9 | **Mock data in build** | `MOCK_USERS = [...]` imported in prod code | `audit_mock_leak.sh` — `MOCK_` pattern forbidden outside `tests/`. |
| 10 | **TODO merged to main** | `# TODO: fix later` | `audit_todo.sh` — new TODOs require PR ack. |
| 11 | **Token in localStorage** | `localStorage.setItem("token", ...)` | `audit_storage.sh` (Plan 3) — forbid `localStorage.setItem` of auth keys; must use `sessionStorage` or httpOnly cookie. |
| 12 | **ORM leak in response** | Returning SQLAlchemy objects without Pydantic response model | FastAPI `response_model=` required; `audit_response_model.py` (Plan 2). |

## How to add an entry

1. PR adding the row above
2. PR must include the interception mechanism (script, lint rule, test)
3. `scripts/audit/run_all.sh` must invoke it

A new entry without mechanical interception is **not** a rule — it's just documentation, and gets added to `docs/review-checklist.md` instead.
````

- [ ] **Step 2: Write `docs/review-checklist.md` (non-mechanical soft checks)**

```markdown
# Review Checklist (non-mechanical)

Items to check during human/agent review. These are judgment calls; if a pattern becomes mechanically checkable, promote it to `docs/conventions/99-anti-laziness.md`.

- [ ] Error codes are meaningful, not `error-1`, `error-2`
- [ ] Log messages have enough context to debug (include IDs, not just "failed")
- [ ] Variable names reflect domain, not types (`userList` → `activeUsers`)
- [ ] New feature has a happy-path e2e or integration test
- [ ] Public API changes are additive or documented as breaking
- [ ] Migrations are reversible (have `downgrade()` where possible)
```

- [ ] **Step 3: Commit**

```bash
git add docs/conventions/99-anti-laziness.md docs/review-checklist.md
git commit -m "docs(conventions): 99 anti-laziness + review checklist"
```

---

## Phase F: CLAUDE.md hierarchy

### Task 20: Write root `CLAUDE.md`

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Write file**

````markdown
# business-template — Agent guide

Generalized business back-office template (OA / approval systems).

## Required reading before editing anything

Read in this order when you start a session:

1. This file
2. `docs/conventions/08-naming-and-layout.md` — where things live
3. Any `docs/conventions/NN-*.md` relevant to your change (see map below)
4. Module-local `CLAUDE.md` where you're editing

## Convention map

| Touching… | Read |
|---|---|
| Pydantic model / validation | `01-schema-validation.md` |
| Delete / state transition | `02-service-guards.md` |
| FE styling or component | `03-ui-primitives.md` |
| Form rendering / validation UX | `04-forms.md` |
| Endpoint / response shape | `05-api-contract.md` |
| Auth / session / password | `06-auth-session.md` |
| Permissions / data scope | `07-rbac.md` |
| Directory / naming | `08-naming-and-layout.md` |
| **Before claiming done** | `99-anti-laziness.md` |

## Hard rules (quick reference — details in convention docs)

- **No hand-written JSON Schema.** Pydantic only.
- **No bare `.all()` / client pagination.** Use `paginate()` / `<DataTable server>`.
- **No inline permission checks.** Use `require_perm` + `apply_scope`.
- **No `except: pass`.** Ever.
- **No MUI / Radix directly in pages.** Only via `@/components/ui/`.
- **No token in `localStorage`.** sessionStorage or httpOnly cookie.

Full enforcement: `scripts/audit/run_all.sh`.

## Before marking a feature complete

1. All tests green: `cd backend && uv run pytest && cd ../frontend && npm test`
2. Types clean: `npm run typecheck`
3. Lint clean: `uv run ruff check . && npm run lint`
4. L1 audits pass: `bash scripts/audit/run_all.sh`
5. **Invoke `convention-auditor` subagent** → `VERDICT: PASS`
6. Only then mark the feature done / open PR

## Dev commands

```bash
# Boot the full stack
docker compose up -d

# Backend shell
docker compose exec backend bash

# Backend tests
docker compose exec backend uv run pytest

# Frontend tests
cd frontend && npm test

# Run all audits
bash scripts/audit/run_all.sh

# Apply migrations
docker compose exec backend uv run alembic upgrade head
```

## Docs

- Specs: `docs/superpowers/specs/`
- Plans: `docs/superpowers/plans/`
- Conventions: `docs/conventions/`
- Auditor subagent: `.claude/agents/convention-auditor.md`
````

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: root CLAUDE.md"
```

### Task 21: Write `backend/CLAUDE.md`

**Files:**
- Create: `backend/CLAUDE.md`

- [ ] **Step 1: Write file**

````markdown
# backend/ — Agent guide

FastAPI + SQLAlchemy 2.0 async + Alembic + Pydantic. Python 3.13, uv.

## Layout (read `docs/conventions/08-naming-and-layout.md`)

```
app/
├── core/       shared infra (config, auth, guards, permissions, pagination, errors, audit, storage, workflow)
└── modules/    feature-first; each dir has models.py schemas.py service.py router.py crud.py
```

Create a new feature → copy `modules/_template/` → fill in. Then register its router in `app/api/v1.py`.

## Non-negotiables

### Schemas / validation (01)
- Pydantic only. Field-level via `Field()`; cross-field via `json_schema_extra={"x-rules": [...]}` from the registry.
- Response models set `alias_generator=to_camel` (inherit from shared `BaseSchema` — Plan 2).

### Endpoints (05, 06, 07)
- Every route has `dependencies=[Depends(require_perm("..."))]` OR `public=True`.
- List endpoints inherit `PaginatedEndpoint` (Plan 2); response shape `{items,total,page,size,hasNext}`.
- Errors via `raise ProblemDetails(code=..., status=..., detail=...)` — never bare `HTTPException` without a code.

### Queries (07)
- Protected resources: `apply_scope(select(X), current_user, perm_code, dept_field)`.
- List: `await paginate(session, stmt, page_query)`.
- Never bare `.all()`. Never `.scalars().all()` without pagination in an endpoint.

### Mutations (02)
- Wrap in `async with session.begin():`.
- Run `__guards__` before write (service base handles this).
- Let audit base emit event automatically.

### No-go
- `except:` or `except Exception: pass` — always re-raise or handle with logging.
- Hard-coded secrets, DSN strings, or magic values — use Settings or enums.
- Returning SQLAlchemy objects directly — always via Pydantic response model.

## Commands

```bash
cd backend
uv sync                        # install
uv run pytest                  # tests
uv run ruff check .            # lint
uv run ruff format .           # format
uv run alembic upgrade head    # migrate
uv run alembic revision --autogenerate -m "msg"
```
````

- [ ] **Step 2: Commit**

```bash
git add backend/CLAUDE.md
git commit -m "docs: backend/CLAUDE.md"
```

### Task 22: Write `frontend/CLAUDE.md`

**Files:**
- Create: `frontend/CLAUDE.md`

- [ ] **Step 1: Write file**

````markdown
# frontend/ — Agent guide

Vite + React 19 + TypeScript + Tailwind + shadcn/ui + RHF + ajv. No Next.js, no MUI.

## Layout (read `docs/conventions/08-naming-and-layout.md`)

```
src/
├── api/            axios client + generated types (DO NOT EDIT generated/)
├── lib/            design-tokens, ajv, auth, utils
├── components/
│   ├── ui/         shadcn facade — import only from here in pages
│   ├── form/       FormRenderer, Field, FieldRegistry
│   ├── table/      DataTable (server pagination only)
│   └── layout/     AppShell, Sidebar, TopBar
└── modules/        feature dirs mirroring backend modules/
```

## Non-negotiables

### UI primitives (03)
- Only import from `@/components/{ui,form,table,layout}` in pages.
- Never `import * from "@radix-ui/..."` in a page. Never `import "@mui/material"` anywhere.
- Variants via `cva`, not ad-hoc className.

### Design tokens
- `src/lib/design-tokens.ts` is the only place colors/spacing/radii are defined. `tailwind.config.ts` reads from it.

### Forms (04)
- Every form is `<FormRenderer schema={...} />`.
- No hand-assembled forms with `<input>` / `<TextField>` in pages.
- No Zod / Yup. ajv only (registered in `@/lib/ajv.ts`).

### Tables
- All list views use `@/components/table/DataTable`. Server-side pagination, sort, filter.
- Never `.slice(start, end)` in a page.

### Auth (06)
- axios interceptor (`@/api/client.ts`) owns all 401 handling; business code doesn't touch 401.
- Access token in memory / sessionStorage. Never `localStorage`.
- Route guards via `<RequirePermission />` wrapper (Plan 3).

### Types
- API types from `src/api/generated/` — never hand-write an API type.
- Run `npm run typecheck` — zero errors or CI fails.

### No-go
- Raw `fetch()` — use axios from `@/api/client.ts`.
- `any` / `@ts-expect-error` without a comment justification.
- Inline styles or arbitrary Tailwind values (`[#fff]`, `[32px]`) — use tokens.

## Commands

```bash
cd frontend
npm install
npm run dev         # vite dev server
npm run build       # prod bundle
npm run typecheck
npm run lint
npm test            # vitest
```
````

- [ ] **Step 2: Commit**

```bash
git add frontend/CLAUDE.md
git commit -m "docs: frontend/CLAUDE.md"
```

### Task 23: Write module-local CLAUDE.md stubs for `components/ui` and `components/form`

**Files:**
- Create: `frontend/src/components/ui/CLAUDE.md`
- Create: `frontend/src/components/form/CLAUDE.md`

- [ ] **Step 1: Write `frontend/src/components/ui/CLAUDE.md`**

```markdown
# components/ui — Primitive facade

This is the **only** place shadcn/ui primitives live. Business code under `src/modules/*` may import from here, but must not import from `@radix-ui/*` directly.

## Adding a new primitive

1. Use shadcn CLI: `npx shadcn add <component>` — lands here.
2. Wrap it if variants are needed (`cva` — no className overrides at call sites).
3. Ensure it reads colors/radii/spacing from `src/lib/design-tokens.ts` (via Tailwind config).
4. Add a minimal Vitest smoke test.

## Extending an existing primitive

- Add a new `cva` variant, NOT a new prop or a className.
- If you can't express it as a variant, reconsider: maybe it's a new primitive, not a variant.

## What does NOT belong here

- Business-specific components (e.g., `UserAvatar` with specific avatar logic) — those go in `modules/user/`.
- Form-specific fields — those go in `components/form/fields/`.
```

- [ ] **Step 2: Write `frontend/src/components/form/CLAUDE.md`**

```markdown
# components/form — JSON-Schema-driven renderer

Every form in the system flows through `FormRenderer` here. See `docs/conventions/04-forms.md`.

## Files (Plan 2 fills these in)

- `FormRenderer.tsx` — recursive renderer reading JSON Schema
- `FieldRegistry.ts` — map `x-widget` → field component
- `fields/{String,Number,Boolean,Date,Enum,File,Array,Object}.tsx` — primitive fields
- `resolver.ts` — ajv resolver for RHF

## Rules

- All fields use `@/components/ui/*` primitives for rendering.
- Cross-field rules go through `@/lib/ajv.ts` (which registers FormRuleRegistry entries).
- Custom widgets extend via `FieldRegistry.register("x-widget", Component)`, not by patching FormRenderer.

## Anti-patterns

- Taking a `render` prop that lets consumers bypass the schema.
- Per-form custom validators (ajv only).
- Using `<input>` anywhere — always `@/components/ui/Input` (via a field component).
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/CLAUDE.md frontend/src/components/form/CLAUDE.md
git commit -m "docs(fe): component-local CLAUDE.md stubs"
```

---

## Phase G: Convention auditor subagent

### Task 24: Write `.claude/agents/convention-auditor.md`

**Files:**
- Create: `.claude/agents/convention-auditor.md`

- [ ] **Step 1: Create dir**

```bash
mkdir -p .claude/agents
```

- [ ] **Step 2: Write file**

````markdown
---
name: convention-auditor
description: >
  Audits code changes against project conventions in docs/conventions/*.md.
  MUST be invoked before marking any feature complete, before commit, and before opening a PR.
  Reads only — does not modify files. Returns PASS or BLOCK verdict.
tools: Bash, Grep, Glob, Read
model: sonnet
---

# Convention Auditor

You audit whether a code change follows the project's conventions. You are **read-only**. You output a structured report; you do not fix violations — you report them so a human or another agent fixes them.

## Required reading (in this order)

1. `CLAUDE.md` (root)
2. All of `docs/conventions/*.md`
3. `docs/conventions/99-anti-laziness.md` is especially important — run every check listed.
4. Module-local `CLAUDE.md` files under any changed directory.

## Your inputs (the invoking agent provides)

- **Change base**: the git ref to diff against (e.g., `main`, or a specific commit). If not given, default to `HEAD~1`.
- **Optional scope**: specific paths to focus on.

## Procedure

1. **Enumerate changes:**
   `git diff --name-only <base>..HEAD` → the files in scope.
2. **Run L1 mechanical audits:**
   `bash scripts/audit/run_all.sh 2>&1`
   Collect the exit status and output. Any failure is an automatic violation.
3. **For each changed file**, determine which conventions apply:

   | File pattern | Applicable convention(s) |
   |---|---|
   | `backend/app/modules/*/schemas.py` | 01, 05 |
   | `backend/app/modules/*/models.py` | 02 (guards), 07 (scope) |
   | `backend/app/modules/*/router.py` | 05, 06, 07 |
   | `backend/app/modules/*/service.py` | 02, 05 |
   | `frontend/src/components/ui/**` | 03 |
   | `frontend/src/components/form/**` | 04 |
   | `frontend/src/modules/**` | 03, 04, 06, 07 (FE side) |
   | `*.py` | 99 (anti-laziness) |
   | `*.{ts,tsx}` | 99 (anti-laziness) |
   | `alembic/versions/*.py` | 99 #4 (index review) |
   | `docs/conventions/*.md` | 08 (layout/naming), 99 changes need PR ack |

4. **Run conventions checks semantically:**
   For each applicable convention, read the relevant section and look for violations in the diff hunks. Focus on what mechanical scripts can't easily catch (naming sanity, scope correctness, error code meaningfulness).

5. **Consult any module-local `CLAUDE.md`** in or above the changed paths.

## Output format (strict)

Produce a single structured report. Use exactly these section headers.

```
# Convention Audit Report

## Changed files (N)
- <path1>
- <path2>
...

## L1 (mechanical) audit result
<pasted last lines of scripts/audit/run_all.sh output; PASS or BLOCK>

## PASS (M)
- [NN-convention-slug] <path>:<line or symbol> — what's right
- ...

## VIOLATIONS (K)
### [NN-convention-slug] <path>:<line>
**Issue:** <one sentence>
**Suggested fix:** <concrete code change>

### [NN-convention-slug] <path>:<line>
...

## UNCERTAIN (J)   (optional; things you couldn't verify and flag for human review)
- [NN-convention-slug] <path>: <reason>

## VERDICT
PASS    (if VIOLATIONS is empty AND L1 passed)
BLOCK   (otherwise)
```

## Decision rules

- Any L1 script failure → automatic `BLOCK`.
- Any semantic violation against a hard rule (tables in convention docs say "Not allowed") → `BLOCK`.
- Items in UNCERTAIN do not block by themselves; the invoking agent decides.
- Be specific: always cite `convention-slug` and file path. Never say "looks fine" without evidence.

## Non-goals

- Do not execute or modify code.
- Do not run tests (that's the invoking agent's job before invoking you).
- Do not speculate about design — you check compliance with documented rules.
- Do not refactor; only report.
````

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/convention-auditor.md
git commit -m "feat(agents): add convention-auditor subagent"
```

---

## Phase H: L1 mechanical audit scripts

### Task 25: Scaffold `scripts/audit/` with `run_all.sh`

**Files:**
- Create: `scripts/audit/README.md`
- Create: `scripts/audit/run_all.sh`

- [ ] **Step 1: Create dir**

```bash
mkdir -p scripts/audit
```

- [ ] **Step 2: Write `scripts/audit/README.md`**

```markdown
# L1 Audit Scripts

Mechanical checks that run in CI and pre-push. Each script must exit non-zero on violation and print offending locations.

Invoke all at once:

```bash
bash scripts/audit/run_all.sh
```

## Inventory (Plan 1)

- `audit_except.sh` — no `except: pass` / `except Exception: pass`
- `audit_todo.sh` — new `TODO|FIXME|XXX` require PR ack
- `audit_mock_leak.sh` — `MOCK_` prefix forbidden outside `tests/`
- `audit_json_schema.sh` — no hand-written `*.schema.json` in sources
- `audit_mui_imports.sh` — `@mui/*` and raw `@radix-ui/*` forbidden in pages
- `audit_pagination_fe.sh` — `paginationMode="client"` forbidden
- `audit_permissions.py` — every FastAPI route has `require_perm` or `public=True`
- `audit_listing.py` — list endpoints return `Page[...]` and use `paginate()`

Later plans add more (guards, magic-strings, n+1, etc.).
```

- [ ] **Step 3: Write `scripts/audit/run_all.sh`**

```bash
#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

FAIL=0

run() {
    local name="$1"; shift
    echo "── $name ──"
    if "$@"; then
        echo "  PASS"
    else
        echo "  FAIL"
        FAIL=1
    fi
}

run "except"         bash scripts/audit/audit_except.sh
run "todo"           bash scripts/audit/audit_todo.sh
run "mock-leak"      bash scripts/audit/audit_mock_leak.sh
run "json-schema"    bash scripts/audit/audit_json_schema.sh
run "mui-imports"    bash scripts/audit/audit_mui_imports.sh
run "pagination-fe"  bash scripts/audit/audit_pagination_fe.sh

if command -v python >/dev/null 2>&1; then
    run "permissions"   python scripts/audit/audit_permissions.py
    run "listing"       python scripts/audit/audit_listing.py
fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "✔ All L1 audits passed."
    exit 0
else
    echo "✘ L1 audits failed."
    exit 1
fi
```

- [ ] **Step 4: Make executable**

```bash
chmod +x scripts/audit/run_all.sh
```

- [ ] **Step 5: Commit**

```bash
git add scripts/audit/README.md scripts/audit/run_all.sh
git commit -m "feat(audit): scaffold scripts/audit with runner"
```

### Task 26: Write `audit_except.sh`

**Files:**
- Create: `scripts/audit/audit_except.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Fails if any backend Python file contains bare `except:` or `except Exception: pass`.
set -u

PATTERN_BARE='^[[:space:]]*except[[:space:]]*:'
PATTERN_SWALLOW='except[[:space:]]+[A-Za-z_]*Exception[[:space:]]*:[[:space:]]*$'

PATHS=("backend/app" "backend/tests")

MATCHES=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE "$PATTERN_BARE|$PATTERN_SWALLOW" "$p" --include="*.py" 2>/dev/null
done)

if [ -n "$MATCHES" ]; then
    echo "Found bare or empty exception handlers:"
    echo "$MATCHES"
    exit 1
fi

# Also catch `except ...: pass` followed by only pass
TWO_LINE=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE -A1 '^[[:space:]]*except[[:space:]].*:[[:space:]]*$' "$p" --include="*.py" 2>/dev/null \
        | grep -B1 '^[[:space:]]*pass[[:space:]]*$' \
        | grep -E 'except' || true
done)

if [ -n "$TWO_LINE" ]; then
    echo "Found except ...: pass patterns:"
    echo "$TWO_LINE"
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable and verify**

```bash
chmod +x scripts/audit/audit_except.sh
bash scripts/audit/audit_except.sh
```

Expected: exit 0 (no matches yet).

- [ ] **Step 3: Smoke test with a deliberate violation**

Create `backend/app/_audit_test.py`:
```python
try:
    x = 1
except:
    pass
```

Run `bash scripts/audit/audit_except.sh`; expect exit 1 and the file listed.

Delete the file:
```bash
rm backend/app/_audit_test.py
```

Run again; expect exit 0.

- [ ] **Step 4: Commit**

```bash
git add scripts/audit/audit_except.sh
git commit -m "feat(audit): audit_except.sh forbids bare/empty except"
```

### Task 27: Write `audit_todo.sh`

**Files:**
- Create: `scripts/audit/audit_todo.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Warns on TODO/FIXME/XXX in source. Fails if count grows without PR ack (ack via `TODO(ack:PR-NNN)`).
set -u

PATHS=("backend/app" "frontend/src")

MATCHES=$(for p in "${PATHS[@]}"; do
    [ -d "$p" ] || continue
    grep -rnE '\b(TODO|FIXME|XXX)\b' "$p" --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null
done)

UNACKED=$(echo "$MATCHES" | grep -vE '\b(TODO|FIXME|XXX)\(ack:' || true)

if [ -n "$UNACKED" ]; then
    echo "Found TODO/FIXME/XXX without PR ack:"
    echo "$UNACKED"
    echo
    echo "Use TODO(ack:PR-123) to acknowledge intentional."
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable and verify**

```bash
chmod +x scripts/audit/audit_todo.sh
bash scripts/audit/audit_todo.sh
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_todo.sh
git commit -m "feat(audit): audit_todo.sh flags unacked TODO/FIXME/XXX"
```

### Task 28: Write `audit_mock_leak.sh`

**Files:**
- Create: `scripts/audit/audit_mock_leak.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Fails if MOCK_ identifiers appear outside tests directories.
set -u

BACKEND_MATCHES=$(grep -rnE '\bMOCK_[A-Za-z0-9_]+' backend/app 2>/dev/null || true)
FRONTEND_MATCHES=$(grep -rnE '\bMOCK_[A-Za-z0-9_]+' frontend/src 2>/dev/null \
    | grep -vE '\.test\.(ts|tsx)$' \
    | grep -vE '__tests__/' \
    || true)

if [ -n "$BACKEND_MATCHES" ] || [ -n "$FRONTEND_MATCHES" ]; then
    echo "MOCK_ identifiers leaked into application code:"
    [ -n "$BACKEND_MATCHES" ] && echo "$BACKEND_MATCHES"
    [ -n "$FRONTEND_MATCHES" ] && echo "$FRONTEND_MATCHES"
    echo
    echo "Mock data belongs in backend/tests/ or *.test.ts files only."
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/audit/audit_mock_leak.sh
bash scripts/audit/audit_mock_leak.sh
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_mock_leak.sh
git commit -m "feat(audit): audit_mock_leak.sh"
```

### Task 29: Write `audit_json_schema.sh`

**Files:**
- Create: `scripts/audit/audit_json_schema.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Fails if any hand-authored *.schema.json exists in sources (except generated/).
set -u

MATCHES=$(find backend/app frontend/src -name '*.schema.json' 2>/dev/null \
    | grep -v '/generated/' || true)

if [ -n "$MATCHES" ]; then
    echo "Hand-written JSON Schema files found. Pydantic is the source of truth."
    echo "$MATCHES"
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/audit/audit_json_schema.sh
bash scripts/audit/audit_json_schema.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_json_schema.sh
git commit -m "feat(audit): audit_json_schema.sh forbids hand-written schemas"
```

### Task 30: Write `audit_mui_imports.sh`

**Files:**
- Create: `scripts/audit/audit_mui_imports.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Fails if @mui is imported anywhere OR @radix-ui is imported outside components/ui.
set -u

MUI=$(grep -rn -E "from ['\"]@mui/" frontend/src 2>/dev/null || true)

RADIX_IN_PAGES=$(grep -rn -E "from ['\"]@radix-ui/" frontend/src 2>/dev/null \
    | grep -vE '^frontend/src/components/ui/' \
    || true)

FAIL=0

if [ -n "$MUI" ]; then
    echo "Found @mui imports (forbidden):"
    echo "$MUI"
    FAIL=1
fi

if [ -n "$RADIX_IN_PAGES" ]; then
    echo "Found @radix-ui imports outside components/ui (forbidden):"
    echo "$RADIX_IN_PAGES"
    FAIL=1
fi

exit $FAIL
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/audit/audit_mui_imports.sh
bash scripts/audit/audit_mui_imports.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_mui_imports.sh
git commit -m "feat(audit): audit_mui_imports.sh"
```

### Task 31: Write `audit_pagination_fe.sh`

**Files:**
- Create: `scripts/audit/audit_pagination_fe.sh`

- [ ] **Step 1: Write script**

```bash
#!/usr/bin/env bash
# Fails if `paginationMode="client"` appears in frontend sources.
set -u

MATCHES=$(grep -rn -E 'paginationMode\s*=\s*["'\'']client["'\'']' frontend/src 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
    echo "Client-side pagination is forbidden. All lists must use server pagination."
    echo "$MATCHES"
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make executable**

```bash
chmod +x scripts/audit/audit_pagination_fe.sh
bash scripts/audit/audit_pagination_fe.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_pagination_fe.sh
git commit -m "feat(audit): audit_pagination_fe.sh"
```

### Task 32: Write `audit_permissions.py`

**Files:**
- Create: `scripts/audit/audit_permissions.py`

- [ ] **Step 1: Write script**

```python
#!/usr/bin/env python
"""Audit: every FastAPI route function must have either
  - a dependency Depends(require_perm(...)) / Depends(require_auth) / Depends(load_in_scope(...))
  - OR an explicit public=True marker in its decorator kwargs

Runs an AST scan over backend/app/modules/*/router.py files.
Since Plan 1 has no router files yet, the script short-circuits to PASS in absence of routers.
Plan 3+ adds real routers; the script then becomes active.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def is_route_decorator(dec: ast.expr) -> tuple[bool, ast.Call | None]:
    if isinstance(dec, ast.Call):
        func = dec.func
        attr = None
        if isinstance(func, ast.Attribute):
            attr = func.attr
        if attr in HTTP_METHODS:
            return True, dec
    return False, None


def has_permission_dep(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg == "dependencies":
            if isinstance(kw.value, ast.List):
                for el in kw.value.elts:
                    src = ast.unparse(el)
                    if "require_perm" in src or "require_auth" in src or "load_in_scope" in src:
                        return True
        if kw.arg == "public":
            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
    return False


def audit_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for dec in node.decorator_list:
                is_route, call = is_route_decorator(dec)
                if is_route and call is not None:
                    if not has_permission_dep(call):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno} "
                            f"endpoint `{node.name}` missing require_perm/public=True"
                        )
    return violations


def main() -> int:
    if not MODULES.exists():
        return 0
    router_files = list(MODULES.glob("*/router.py"))
    if not router_files:
        return 0

    all_violations: list[str] = []
    for f in router_files:
        all_violations.extend(audit_file(f))

    if all_violations:
        print("Endpoints missing permission/public marker:")
        for v in all_violations:
            print("  " + v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run**

```bash
python scripts/audit/audit_permissions.py
```

Expected: exit 0 (no router files yet in Plan 1).

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_permissions.py
git commit -m "feat(audit): audit_permissions.py"
```

### Task 33: Write `audit_listing.py`

**Files:**
- Create: `scripts/audit/audit_listing.py`

- [ ] **Step 1: Write script**

```python
#!/usr/bin/env python
"""Audit: list endpoints (GET on /<resource>) must return `Page[...]` or similar,
never bare list[...] or List[...].

Heuristic: scan router.py functions decorated with @router.get(path) where path
doesn't include an `{id}` segment, and check their return annotation.

Short-circuits to PASS when no router files exist.
"""
from __future__ import annotations
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "backend" / "app" / "modules"


def get_route_path(dec: ast.Call) -> str | None:
    if not dec.args:
        return None
    if isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        return dec.args[0].value
    return None


def is_list_path(path: str) -> bool:
    return "{" not in path


def audit_file(path: Path) -> list[str]:
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func = dec.func
                if isinstance(func, ast.Attribute) and func.attr == "get":
                    route = get_route_path(dec)
                    if route and is_list_path(route):
                        # Check return annotation
                        ann = node.returns
                        if ann is None:
                            violations.append(
                                f"{path.relative_to(ROOT)}:{node.lineno} "
                                f"list endpoint `{node.name}` has no return annotation"
                            )
                            continue
                        src = ast.unparse(ann)
                        if "Page" not in src:
                            violations.append(
                                f"{path.relative_to(ROOT)}:{node.lineno} "
                                f"list endpoint `{node.name}` returns `{src}`, expected Page[...]"
                            )
    return violations


def main() -> int:
    if not MODULES.exists():
        return 0
    router_files = list(MODULES.glob("*/router.py"))
    if not router_files:
        return 0

    all_violations: list[str] = []
    for f in router_files:
        all_violations.extend(audit_file(f))

    if all_violations:
        print("List endpoints with non-paginated response type:")
        for v in all_violations:
            print("  " + v)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run**

```bash
python scripts/audit/audit_listing.py
```

Expected: exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/audit/audit_listing.py
git commit -m "feat(audit): audit_listing.py"
```

### Task 34: Smoke-run the full audit suite

- [ ] **Step 1: Run**

```bash
bash scripts/audit/run_all.sh
```

Expected output ends with `✔ All L1 audits passed.` and exit code 0.

- [ ] **Step 2: Commit any permissions fixes if needed**

(No change expected; this task is a verification gate.)

---

## Phase I: CI

### Task 35: Write GitHub Actions workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create dir**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          python-version: "3.13"
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest -q
        env:
          SECRET_KEY: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
          APP_ENV: test

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run typecheck
      - run: npm run lint
      - run: npm test

  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: bash scripts/audit/run_all.sh
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: lint, test, audit workflows"
```

---

## Phase J: Final verification

### Task 36: End-to-end foundation smoke

- [ ] **Step 1: Tear down and rebuild the stack from scratch**

```bash
docker compose down -v
docker compose up -d --build
```

Wait up to 2 minutes for ClamAV.

- [ ] **Step 2: Verify service healthz**

```bash
docker compose ps
curl -sf http://localhost:8080/healthz
```

Expected: all services `healthy`; curl returns `{"status":"ok"}`.

- [ ] **Step 3: Visit frontend**

Open http://localhost:8080 in a browser. You should see "business-template — foundation ready."

- [ ] **Step 4: Run backend tests inside container**

```bash
docker compose exec backend uv run pytest -q
```

Expected: `1 passed` (healthz test).

- [ ] **Step 5: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: `1 passed` (App smoke test).

- [ ] **Step 6: Run full audit suite**

```bash
cd ..
bash scripts/audit/run_all.sh
```

Expected: `✔ All L1 audits passed.`

- [ ] **Step 7: Invoke convention-auditor subagent (L2)**

Via the Agent tool:

```
Agent(
  subagent_type: "convention-auditor",
  description: "Audit foundation plan completion",
  prompt: "Audit the current state against docs/conventions/*.md.
           Base = initial commit; HEAD = tip.
           Expected verdict: PASS (this is the foundation plan,
           not yet executing any business module code)."
)
```

Expected verdict: **PASS**. If BLOCK, fix each violation, commit, and re-run.

- [ ] **Step 8: Tag**

```bash
docker compose down
git tag v0.1.0-foundation
```

- [ ] **Step 9: Final commit / record**

```bash
git log --oneline
```

Expected: clean history of ~36 commits, ending at the foundation tag.

---

## Spec coverage check (self-review)

Running this plan satisfies these spec sections:

| Spec section | Covered by task(s) |
|---|---|
| §2 Tech stack | 2, 5, 10 (docker services), 11–19 (conventions docs fix choices) |
| §3 Runtime architecture | 7, 8, 9, 10 |
| §3.2 Deployment topology (dev) | 10 |
| §5.0 Guiding principle (3-layer enforcement) | 11–19 + 24 + 25–34 |
| §5.1 Schema contract | 11 (convention doc) — implementation in Plan 2 |
| §5.2 Service guards | 12 (convention doc) — implementation in Plan 2 |
| §5.3 UI primitives | 13 (convention doc); token SSOT in Task 5 |
| §5.4 Forms | 14 (convention doc) — implementation in Plan 2 |
| §5.5 API contract | 15 (convention doc) — implementation in Plan 2 |
| §5.6 Auth / session | 16 (convention doc) — implementation in Plan 3 |
| §5.7 RBAC | 17 (convention doc) — implementation in Plan 4 |
| §5.8 Layout / naming | 18 (convention doc) + monorepo scaffold 2, 5 |
| §5.9 Anti-laziness | 19 (convention doc + review-checklist) + audit scripts 26–33 |
| §7 Convention auditor | 24 + 25–34 + 35 (CI) |
| §8 Foundation deliverables | all tasks |

### Spec items DEFERRED to later plans (not a gap)

- §5.1 FormRuleRegistry **implementation** → Plan 2
- §5.2 ServiceGuardRegistry + `GuardViolationError` → Plan 2
- §5.4 FormRenderer + ajv resolver → Plan 2
- §5.5 Problem Details + PaginatedEndpoint + `paginate()` → Plan 2
- §5.6 auth flows & endpoints → Plan 3
- §5.7 `require_perm` + `apply_scope` + permission seed → Plan 2 (core) + Plan 4 (RBAC module)
- §6 Workflow DSL library → Plan 6
- Attachment / audit_log / notification services → Plan 5
- Business modules (user, dept, role, workflow_example) → Plans 3–6

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-plan1-foundation.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
