---
slice: contract-management
project: office-hero
lld: user/slices/023-slice.contract-management.md
dependencies: [2, 3, 4, 5, 9, 10, 12]
projectState: >
  All backend slices (auth, DB, jobs, customers) complete. Contract management
  fully implemented — model, repository, service, routes, frontend, and tests
  all landed. Verified passing in the 506-test suite.
dateCreated: 20260612
dateUpdated: 20260616
status: complete
docType: tasks
---

## Context Summary

Slice 023 implements recurring service agreements (PestPac-style Contracts) that
generate Jobs on a schedule. A Contract belongs to a Customer + Location, carries
a `frequency` and `next_due` date, and produces Jobs via an explicit idempotent
generation pass triggered via API or CLI.

All deliverables are complete and verified.

---

## Task Breakdown

### Backend

- [x] `core/contract_status.py` — `ContractStatus` enum + `can_transition()` + `is_terminal()`
- [x] `core/contract_frequency.py` — `ContractFrequency` enum + `advance_date()` (calendar-safe, anchor-day clamped)
- [x] `models/contract.py` — `Contract` ORM model with all columns (id, tenant_id, customer_id, location_id, industry, title, frequency, start_date, next_due, end_date, status, paused_at, ended_at, end_reason, custom_fields, external_id, created_by_user_id)
- [x] `models/job.py` — nullable `contract_id` FK column added
- [x] `alembic/versions/0011_contracts.py` — contracts table + RLS policy + CHECK constraints + indexes + ALTER TABLE jobs ADD COLUMN contract_id
- [x] `repositories/contract_repository.py` — `ContractRepositoryProtocol` + `ContractRepository` (SQLAlchemy) + `InMemoryContractRepository`; methods: create, get_by_id, list, update_fields, update_status, list_due
- [x] `services/contract_service.py` — create (tenant + ownership checks, template validation), get, list, update, pause/resume/end transitions, `generate_due_jobs` (catch-up, 24-iteration guard, idempotent, auto-end on end_date, audit events)
- [x] `api/schemas/contract.py` — ContractCreate, ContractUpdate, ContractEndRequest, GenerateJobsRequest, ContractSummary, ContractRead, ContractList, GenerateJobsResponse
- [x] `api/routes/contracts.py` — POST /contracts, GET /contracts, GET /contracts/{id}, PATCH /contracts/{id}, POST /contracts/{id}/pause|resume|end, POST /contracts/generate-jobs
- [x] Wired into `api/app.py` and `api/state.py`
- [x] `core/exceptions.py` — ContractNotFoundError, InvalidContractTransitionError

### Tests

- [x] `tests/unit/test_contract_frequency.py` — advance_date matrix incl. month-end clamping and leap years
- [x] `tests/unit/test_contract_service.py` — create validation, transition matrix, update immutability, generation (single, catch-up, paused skip, auto-end, idempotent re-run, audit events)
- [x] `tests/api/test_contracts_api.py` — 401/403/404 RBAC + cross-tenant, CRUD, filters/pagination, generate endpoint

### Frontend

- [x] `apps/admin-web/src/api.ts` — Contract types (ContractStatus, ContractFrequency, ContractSummary, ContractRead) + API functions (listContractsApi, createContractApi, pauseContractApi, resumeContractApi, endContractApi, generateContractJobsApi)
- [x] `apps/admin-web/src/pages/ContractsPage.tsx` — list with status filter + search + next-due column + frequency labels + status badges; Create modal (customer → location pickers, frequency, start date, service type, duration, priority); row actions (pause/resume/end); "Generate due jobs" showing job count created
- [x] Nav registration (Contracts link in NavShell)
