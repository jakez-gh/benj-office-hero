"""Saga Recovery Procedures

This guide covers how to diagnose and recover from saga failures,
stuck compensations, and dead-letter events.
"""

# Saga Recovery & Troubleshooting Procedures

## Issue 1: Saga Stuck in COMPENSATING State

**Symptoms**: Saga appears frozen, never reaches DONE or FAILED.

**Root Cause**: Compensation function is hanging (blocking I/O, network timeout).

### Diagnosis: Stuck Saga

```python
# Check saga status via API or CLI
from office_hero.services.saga_service import SagaService
from office_hero.repositories.mocks import MockSagaRepository

saga_service = SagaService(saga_repo=MockSagaRepository())
saga = await saga_service.get_saga_status(saga_id=UUID("..."))

if saga.status == SagaStatus.COMPENSATING:
    print(f"Stuck at step {saga.current_step}")
    print(f"Error: {saga.last_error}")
```

### Recovery

**Option 1**: Timeout & let retry logic kick in

Sagas have a timeout wrapper (TBD). If compensation doesn't complete within
timeout (default: 30s), the saga is marked as `FAILED` with
`compensation_status = 'timeout'`.

**Option 2**: Manual intervention

```python
# Operator connects to admin CLI
python -m tools.cli admin show-dead-letters --type compensating

# Manually completes the compensation
# (e.g., calls ServiceTitan API to delete org)
# Then marks saga as FAILED in database

UPDATE saga_log
SET status = 'FAILED',
    compensation_status = 'manual'
WHERE saga_id = '...' AND status = 'COMPENSATING';
```

**Option 3**: Replay saga

If the underlying error is transient:

```python
# Modify idempotency_key if you want a fresh execution (NOT recommended—use Opt 1/2)
# Just retry with same key; idempotency service returns cached result

result = await saga_service.execute_saga(saga_definition)
# Same saga_id, same behavior
```

---

## Issue 2: Compensation Fails (SagaCompensationFailedError)

**Symptoms**: Exception thrown with message "Saga X step 'compensate' failed".

**Root Cause**: Compensating step raised an exception (e.g., ServiceTitan returned 500).

### Diagnosis: Compensation Failure

```sql
SELECT * FROM saga_log
WHERE saga_id = '...'
  AND compensation_status = 'FAILED';

-- Review last_error field for details
```

### Recovery: 3-Step Process

**Step 1: Assess Impact**

Determine what was compensated successfully before failure:

```python
# Pseudo-code: Check external systems

# ServiceTitan
st_orgs = st_api.list_orgs(tenant_id)
if not st_orgs:
    print("✓ ServiceTitan org was deleted (compensation succeeded)")
else:
    print("✗ ServiceTitan org still exists (compensation failed at this step)")

# PestPac
pest_jobs = pest_api.list_jobs(sync_id)
if not pest_jobs:
    print("✓ PestPac jobs were deleted")
else:
    print("✗ PestPac jobs still exist")
```

**Step 2: Manual Cleanup**

Complete any remaining compensation steps manually:

```bash
# Example: Delete ServiceTitan org if compensation failed there
curl -X DELETE https://api.servicetitan.com/orgs/{org_id} \
  -H "Authorization: Bearer {token}"

# Update saga_log to reflect the manual cleanup
UPDATE saga_log
SET compensation_status = 'manual_completed'
WHERE saga_id = '...';
```

**Step 3: Alert Monitoring**

Log incident for post-mortem:

```text
INCIDENT REPORT:
- Saga ID: ...
- Type: create_tenant
- Failed step: create_servicetitan_org
- Compensation failed at: 18:23:45 UTC
- Root cause: ST API returned 503 (Service Unavailable)
- Manual action: Deleted org ST-12345 via API
- Resolution time: 5 minutes
- Follow-up: Configure ST API retry logic with exponential backoff
```

---

## Issue 3: Missing Events in Outbox

**Symptoms**: Expected outbox event never appears; downstream system doesn't receive notification.

**Root Cause**: Event creation failed (DB transaction rolled back) or poller crashed.

### Diagnosis: Missing Outbox Event

```python
# Check outbox status
from office_hero.repositories.mocks import MockOutboxRepository

repo = MockOutboxRepository()
pending = await repo.get_pending(tenant_id=tenant_id, limit=100)

if not pending:
    print("No pending events")

    # Check dead-letter
    dead = await repo.get_dead_letters(tenant_id=tenant_id)
    if dead:
        print(f"Event moved to dead-letter: {dead[0]['dead_letter_reason']}")
```

### Recovery: Missing Outbox Event

**Procedure**: Replay Event

```python
# Operator fetches saga_log
saga = await saga_service.get_saga_status(saga_id)

if saga.status == SagaStatus.DONE and not saga.context.get("event_sent"):
    # Event was never created; manually create it
    event = await outbox_repo.create(
        tenant_id=saga.tenant_id,
        event_type="tenant.created",
        payload={
            "saga_id": saga.saga_id,
            "tenant_id": saga.context["tenant_id"],
            "timestamp": datetime.now().isoformat(),
        },
        idem_key=uuid4(),  # New key to avoid dedup
    )
    print(f"Event {event['id']} created; outbox poller will process it")
```

---

## Issue 4: Idempotency Key Reuse (Wrong Step)

**Symptoms**: Exception: "Key reused: 'create_st_org' vs 'create_pp_job'".

**Root Cause**: Same `idempotency_key` used for two different steps (config error).

### Diagnosis: Idempotency Key Reuse

```python
from office_hero.services.idempotency_service import IdempotencyService

svc = IdempotencyService()

# Check cache
if (key := UUID("...")) in svc.cache:
    step_name, result = svc.cache[key]
    print(f"Key {key} cached for step '{step_name}'")
    print(f"Attempting to reuse for different step → ERROR")
```

### Recovery: Idempotency Key Reuse

Replace the idempotency keys in the saga definition:

```python
# WRONG
saga = SagaDefinition(
    sagatype="...",
    steps=[
        SagaStep(..., idempotency_key=SAME_KEY, ...),
        SagaStep(..., idempotency_key=SAME_KEY, ...),  # ❌ Reused!
    ],
)

# CORRECT
saga = SagaDefinition(
    saga_type="...",
    steps=[
        SagaStep(..., idempotency_key=uuid4(), ...),
        SagaStep(..., idempotency_key=uuid4(), ...),  # ✓ Unique
    ],
)
```

---

## Issue 5: Database Deadlock During Compensation

**Symptoms**: Compensation times out; `20P000: Serialization failure`.

**Root Cause**: Compensation query locks rows that other sagas are accessing.

### Prevention

1. **Use advisory locks**: Lock by saga ID, not row ID
2. **Minimize lock duration**: Keep compensation queries fast
3. **Escalate carefully**: Don't hold locks across steps

### Recovery: Deadlock Recovery

```python
# If saga is stuck in deadlock
# 1. Force timeout (saga marks as FAILED)
# 2. Retry compensation logic (may succeed 2nd time)
# 3. If still fails → manual cleanup (Issue 2)

# Example: Force saga to FAILED state
UPDATE saga_log
SET status = 'FAILED',
    last_error = 'Deadlock detected; manual recovery required',
    compensation_status = 'deadlock'
WHERE saga_id = '...';
```

---

## Issue 6: Partial Compensation (Some Steps Succeeded, Some Failed)

**Symptoms**: Saga is in FAILED state, but external systems are partially compensated.

**Root Cause**: Compensation failed mid-way (e.g., step 2 of 3 failed).

### Diagnosis: Partial Compensation

```sql
SELECT * FROM saga_log
WHERE saga_id = '...'
  AND compensation_status = 'PARTIAL';

-- Review which steps were compensated
-- saga_log.context has history of each step
```

### Recovery: Partial Compensation

Complete remaining compensation steps:

```python
# Step 1: Deleted ✓
# Step 2: Failed ✗ (ServiceTitan API error)
# Step 3: Not attempted ✗

# Operator must:
# 1. Manually complete step 2 (delete from ST)
# 2. Execute step 3 compensation (delete from PP)
# 3. Update saga_log to mark as 'manual_completed'

UPDATE saga_log
SET compensation_status = 'manual_completed',
    updated_at = NOW()
WHERE saga_id = '...';
```

---

## Runbook: Quick Recovery Steps

### For Stuck Saga (COMPENSATING)

```bash
1. Check logs:  tail -f logs/saga_*.log | grep "saga_id"
2. Timeout:     Wait 30s (default) for timeout to trigger
3. Verify:      SELECT * FROM saga_log WHERE saga_id = '...' AND status = 'FAILED'
4. Alert:       PagerDuty or #alerts Slack channel
```

### For Failed Compensation

```bash
1. Assess:      Check external systems (ST, PP, Jobber)
2. Manual fix:   Delete/rollback any partial state
3. Mark done:    UPDATE saga_log SET compensation_status = 'manual_completed'
4. Monitor:      Watch for cascading failures (dependent sagas)
```

### For Dead-Letter Event

```bash
1. Review:      SELECT * FROM dead_letter WHERE event_id = '...'\G
2. Understand:  Why did event fail? (Parsing? Network? )
3. Fix root:    If transient, retry. If semantic, fix payload.
4. Retry:       python -m tools.cli admin retry-dead-letter {event_id}
```

---

## Escalation Matrix

| Issue | Severity | Time to Resolve | Escalate To |
|-------|----------|-----------------|-------------|
| Stuck COMPENSATING (< 5 min) | P2 | < 15 min | On-call Engineer |
| Failed Compensation | P1 | < 5 min | Ops + Engineering |
| Partial Compensation | P1 | < 10 min | Ops Lead + CTO |
| Dead-Letter Rate > 10/min | P1 | < 2 min | VP Engineering |
| Mass Saga Failures (> 100/min) | P0 | < 1 min | Incident Commander |

---

## Prevention: Best Practices

1. **Monitor compensation failures**: Alert if compensation_failed count > 1/hour
2. **Test compensation regularly**: Chaos engineering: inject failures mid-saga
3. **Use unique idempotency keys**: Generate UUID per step, never reuse
4. **Version your sagas**: Support A/B sagas if schema changes
5. **Document compensations**: Every step must explain how to undo it manually
