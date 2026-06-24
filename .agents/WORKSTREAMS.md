# Workstreams

Each row is a claimable unit of work. Status: `open` | `claimed:<agent-id>` | `done`.

| ID | Status | Description | Slice / File |
|----|--------|-------------|--------------|
| WS-01 | open | Run full test suite; fix any failures; report coverage | `pytest` |
| WS-02 | open | Alembic migration: create `jobber_credentials` table (migration 0018) | `alembic/` |
| WS-03 | open | Integration tests for tenant admin routes against a real DB (Slice 29 follow-up) | `tests/integration/` |
| WS-04 | open | BackOfficeSyncService: write unit tests for lazy `_adapter_name` | `tests/` |
| WS-05 | done | Code review: `sq review code --diff origin/main` — report findings, fix nits | CI gate |
| WS-06 | open | Route reorder UX hint — decide and implement (RoutesPage.tsx) | `apps/admin-web/src/pages/RoutesPage.tsx` |
| WS-07 | claimed:gamma | Verify TenantsPage renders correctly: start dev server, smoke-test the UI | `apps/admin-web/` |
| WS-08 | done | Update DEVLOG.md with Slices 29 + 30 summary | `DEVLOG.md` |

Agents: claim a row by editing its Status cell and pushing immediately.
