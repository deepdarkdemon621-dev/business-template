# Audit log retention

## Policy

Audit events are retained for **1 year**. Rows older than 365 days are deleted by an external pruning job.

## Manual invocation

```bash
docker compose exec backend uv run python -m typer app.cli_commands.audit run --older-than-days 365
```

To dry-run with a shorter cutoff for testing:

```bash
docker compose exec backend uv run python -m typer app.cli_commands.audit run --older-than-days 7 --chunk-size 500
```

## Recommended schedule

Option A — yearly (simplest): run once per year during a low-traffic window.

```
0 3 1 1 * docker compose exec backend uv run python -m typer app.cli_commands.audit run --older-than-days 365
```

Option B — monthly (smoother disk usage):

```
0 3 1 * * docker compose exec backend uv run python -m typer app.cli_commands.audit run --older-than-days 365
```

## Operational notes

- The pruning job commits in 10 000-row chunks. A table with millions of rows may take several minutes and briefly hold row locks on each chunk — prefer off-hours.
- Every prune invocation emits a self-audit event (`audit.pruned`) containing the cutoff and deleted count.
- Compliance note: if legal/APPI requirements demand longer retention, extend `--older-than-days` accordingly. Shortening retention requires no migration, but be aware that the prune itself is irreversible.
