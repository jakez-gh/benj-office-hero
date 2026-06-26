# Workstreams

Each row is a claimable unit of work. Status: `open` | `claimed:<agent-id>` | `done`.

| ID | Status | Description | File |
| -- | ------ | ----------- | ---- |
| WS-01 | done | Run full test suite; fix any failures | `pytest` |
| WS-02 | done | Alembic migration for jobber_credentials (0016 already did it) | `alembic/` |
| WS-03 | open | Integration tests for tenant admin routes against real DB | `tests/integration/` |
| WS-04 | done | Unit tests for BackOfficeSyncService._adapter_name | `tests/` |
| WS-05 | done | Code review; fix nits | CI gate |
| WS-06 | open | Route reorder UX hint | `apps/admin-web/src/pages/RoutesPage.tsx` |
| WS-07 | done | Smoke-test TenantsPage UI | `apps/admin-web/` |
| WS-08 | done | DEVLOG entry for Slices 29+30 | `DEVLOG.md` |
| WS-09 | done | UI-01 mobile nav hamburger drawer | `NavShell.tsx` |
| WS-10 | done | UI-02/03/04/05 table scroll, add buttons, empty-state CTAs | `apps/admin-web/src/pages/` |
| WS-11 | done | UI-06/07 error style + Operator retry | `apps/admin-web/src/pages/` |
| WS-12 | done | UI-08/09/10 button labels, onboarding, forgot-password | `apps/admin-web/src/` |
| WS-13 | done | QA-01 screenshots-seeded: add /tenants + /operator routes | `apps/admin-web/src/e2e/` |
| WS-14 | done | QA-02 Demo 4: Tenants + Operator Dashboard | `apps/admin-web/src/e2e/` |

Agents: claim a row by editing Status and pushing immediately.
