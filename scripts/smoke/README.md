# Browser Smoke Tests

Playwright-driven end-to-end smoke scripts run against the live `docker compose` stack.
Unlike vitest, these exercise the actual axios client, real nginx routing, and the mounted
React tree — catching bugs that mocked unit tests miss.

## Prerequisites

- `docker compose up -d` running (stack healthy)
- Google Chrome installed (driven via Playwright's `channel: "chrome"`; no Chromium download)
- Node ≥ 18

## Setup

```bash
cd scripts/smoke
npm install
```

## Run

```bash
node plan5-smoke.mjs
```

Screenshots land in `out/` (one per step, plus `FAIL_*.png` on failure).

## Scripts

- `plan5-smoke.mjs` — Admin user CRUD + role assignment + mustChangePassword flow + self-protection + soft-delete filter (14 steps)
- `plan6-smoke.mjs` — Department tree CRUD: login → tree renders → create child + grandchild → rename → cycle-guard dialog → has-children delete block → delete leaf → toggle inactive filter → logout (12 steps)
