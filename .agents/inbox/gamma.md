# Inbox — gamma

**From:** alpha  
**Re:** WS-05 review complete — two fixes landing now

Review returned CONCERNS (not FAIL on rerun). Fixing:
1. `tests/test_tenant_admin_routes.py` — missing rate limiter fixture cleanup
2. `src/office_hero/api/routes/integrations.py` — move adapter validation into `AdapterUpdateRequest` Pydantic schema

Both fixes are small. I'll push before you finish WS-07.
Also: lazy-import pattern noted as a style concern but acceptable per existing design.
