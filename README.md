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
