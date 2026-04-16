# Review Checklist (non-mechanical)

Items to check during human/agent review. These are judgment calls; if a pattern becomes mechanically checkable, promote it to `docs/conventions/99-anti-laziness.md`.

- [ ] Error codes are meaningful, not `error-1`, `error-2`
- [ ] Log messages have enough context to debug (include IDs, not just "failed")
- [ ] Variable names reflect domain, not types (`userList` → `activeUsers`)
- [ ] New feature has a happy-path e2e or integration test
- [ ] Public API changes are additive or documented as breaking
- [ ] Migrations are reversible (have `downgrade()` where possible)
