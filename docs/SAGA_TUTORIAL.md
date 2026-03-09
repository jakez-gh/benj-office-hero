"""Office Hero Saga Pattern Tutorial

This guide explains the saga pattern implementation in Office Hero,
why it matters, and how to use it for distributed transactions.
"""

# Saga Pattern for Distributed Transactions

## Overview

The **saga pattern** enables Office Hero to coordinate operations across multiple
systems (ServiceTitan, PestPac, Jobber) as atomic transactions. If any step fails,
the saga automatically compensates (rolls back) all prior steps.

### Without Sagas (❌ Broken)

```plaintext
1. Create customer in Office Hero DB    ✅
2. Create tenant in ServiceTitan        ✅
3. Sync job to PestPac                  ❌ FAILS

→ Office Hero has customer record, but ServiceTitan & PestPac are out of sync
→ Manual cleanup required; data corruption risk
```

### With Sagas (✅ Reliable)

```plaintext
1. Create customer in Office Hero DB    ✅
2. Create tenant in ServiceTitan        ✅
3. Sync job to PestPac                  ❌ FAILS

→ Automatic compensation:
   - Undo step 2: Delete tenant from ServiceTitan
   - Undo step 1: Mark customer as failed
→ All systems consistent; clean failure
```

## Architecture

### Components

1. **SagaService**: Orchestrates step execution and compensation
2. **SagaStep**: Individual operation (execute + compensate functions)
3. **IdempotencyService**: Caches step results to prevent duplicates on retry
4. **OutboxRepository**: Stores events for asynchronous processing
5. **MockSagaRepository**: In-memory repo for testing (real DB TBD)

### Flow

```plaintext
┌─────────────────────────────────────────────────────────────┐
│ SagaService.execute_saga(SagaDefinition)                    │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │ Step 1      │
                    │ execute()   │──┐
                    └─────────────┘  │
                           │         │
                           ✅        │ context merge
                           │         │
                    ┌──────▼──────┐ │
                    │ Step 2      │ │
                    │ execute()   │─┼──┐
                    └─────────────┘ │  │
                           │        │  │
                           ✅       │  │ context merge
                           │        │  │
                    ┌──────▼──────┐ │  │
                    │ Step 3      │ │  │
                    │ execute()   │─┼──┼──── ❌ FAILS
                    └─────────────┘ │  │
                                    │  │
            compensation in reverse │  │
                    ┌───────────────┴──┴──┐
                    │ Step 2 compensate() │
                    │ DELETE from ST      │
                    └─────────────────────┘
                           │
                           ✅
                           │
                    ┌──────▼──────────────┐
                    │ Step 1 compensate() │
                    │ MARK as failed      │
                    └─────────────────────┘
                           │
                           ✅
                           │
                        SAGA FAILED
                    (all systems consistent)
```

## Example: Create Tenant Saga

### Definition

```python
from uuid import uuid4
from office_hero.sagas.core import SagaDefinition, SagaStep, StepStatus

async def create_office_hero_tenant(ctx: dict) -> dict:
    """Step 1: Create tenant record in Office Hero."""
    tenant_id = ctx.get("new_tenant_id")
    # DB write here
    return {"oh_tenant_created": True, "tenant_id": tenant_id}

async def undo_office_hero_tenant(ctx: dict) -> dict:
    """Compensation: Delete tenant from Office Hero."""
    tenant_id = ctx["tenant_id"]
    # DB delete here
    return {}

async def create_servicetitan_org(ctx: dict) -> dict:
    """Step 2: Create organization in ServiceTitan API."""
    tenant_id = ctx["tenant_id"]
    # API call to ServiceTitan
    st_org_id = "ST-12345"  # from API response
    return {"st_org_id": st_org_id}

async def undo_servicetitan_org(ctx: dict) -> dict:
    """Compensation: Delete organization from ServiceTitan."""
    st_org_id = ctx["st_org_id"]
    # API call to delete
    return {}

# Define saga
create_tenant_saga = SagaDefinition(
    saga_type="create_tenant",
    steps=[
        SagaStep(
            name="create_oh_tenant",
            execute=create_office_hero_tenant,
            compensate=undo_office_hero_tenant,
            idempotency_key=uuid4(),
            status=StepStatus.PENDING,
        ),
        SagaStep(
            name="create_st_org",
            execute=create_servicetitan_org,
            compensate=undo_servicetitan_org,
            idempotency_key=uuid4(),
            status=StepStatus.PENDING,
        ),
    ],
    context={
        "new_tenant_id": uuid4(),
        "admin_email": "admin@example.com",
    },
)
```

### Execution

```python
from office_hero.services.saga_service import SagaService
from office_hero.repositories.mocks import MockSagaRepository

saga_service = SagaService(saga_repo=MockSagaRepository())

try:
    result = await saga_service.execute_saga(create_tenant_saga)
    print(f"Saga {result.saga_id} completed successfully")
    print(f"Context: {result.context}")
    # Now create Jobber account, send welcome email, etc.
except SagaCompensationFailedError:
    # Critical: compensation failed → manual intervention needed
    # Alert ops team, log event to dead-letter queue
    raise
except SagaError as e:
    # Forward failure: saga rolled back cleanly
    # Safe to retry or ask user to try again
    print(f"Saga failed and rolled back: {e.message}")
```

### Context Flow

Step 1 returns `{"oh_tenant_created": True, "tenant_id": uuid}` →
merged into context → Step 2 sees it as `ctx["tenant_id"]`

```plaintext
Initial:    {"new_tenant_id": "UUID-X", "admin_email": "..."}
After S1:   {..., "oh_tenant_created": True}
After S2:   {..., "st_org_id": "ST-12345"}
Final:      {all above}
```

## Key Guarantees

### 1. Atomicity

Either all steps succeed, or all are undone. No partial state.

### 2. Idempotency

Retrying a saga with the same key doesn't create duplicates:

```python
# First call
result1 = await saga_service.execute_saga(saga)

# Network timeout before return; caller retries
result2 = await saga_service.execute_saga(saga)

# result1 == result2 (same saga_id); no double-create
```

### 3. Tenancy Isolation

Each saga is scoped to a `tenant_id`:

```python
# Tenant A's saga never sees Tenant B's data
saga_a = SagaDefinition(saga_type="...", context={"tenant_id": "A"})
saga_b = SagaDefinition(saga_type="...", context={"tenant_id": "B"})
```

### 4. Compensation Reliability

If compensation itself fails (e.g., ServiceTitan API is down), the
saga is moved to **dead-letter** for operator intervention:

```python
try:
    await saga_service.compensate(saga_context, saga_definition, failed_step_idx)
except SagaCompensationFailedError:
    # Saga status = FAILED, compensation_status = FAILED
    # Logged to dead-letter; operator reviews and fixes manually
```

## Testing

### Unit Test Pattern

```python
import pytest
from office_hero.services.saga_service import SagaService
from office_hero.repositories.mocks import MockSagaRepository

@pytest.mark.asyncio
async def test_saga_success():
    """Test happy path."""
    saga_service = SagaService(saga_repo=MockSagaRepository())

    async def noop_execute(ctx: dict) -> dict:
        return {"done": True}

    async def noop_compensate(ctx: dict) -> dict:
        return {}

    saga = SagaDefinition(
        saga_type="test",
        steps=[
            SagaStep(
                name="test_step",
                execute=noop_execute,
                compensate=noop_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            )
        ],
        context={},
    )

    result = await saga_service.execute_saga(saga)
    assert result.status == SagaStatus.DONE


@pytest.mark.asyncio
async def test_saga_compensation():
    """Test failure + compensation."""
    saga_service = SagaService(saga_repo=MockSagaRepository())

    compensated = False

    async def failing_step(ctx: dict) -> dict:
        raise ValueError("Step failed")

    async def tracking_compensate(ctx: dict) -> dict:
        nonlocal compensated
        compensated = True
        return {}

    saga = SagaDefinition(
        saga_type="comp_test",
        steps=[
            SagaStep(
                name="test_step",
                execute=failing_step,
                compensate=tracking_compensate,
                idempotency_key=uuid4(),
                status=StepStatus.PENDING,
            )
        ],
        context={},
    )

    result = await saga_service.execute_saga(saga)
    assert result.status == SagaStatus.FAILED
    assert compensated is True
```

### Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_create_tenant_integration():
    """Test full create-tenant saga with real(ish) operations."""
    # Set up mocks for ServiceTitan, PestPac, etc.
    # Execute saga
    # Verify all external calls were made
    # Verify DB state
```

## Monitoring & Debugging

### Saga Execution Log

Each saga writes an audit trail to `saga_log` table:

```sql
SELECT * FROM saga_log
WHERE saga_type = 'create_tenant'
  AND status IN ('FAILED', 'COMPENSATING')
  AND created_at > NOW() - INTERVAL 1 HOUR;
```

### Dead-Letter Queue

Sagas that fail **compensation** → `dead_letter` table:

```sql
SELECT * FROM dead_letter
WHERE saga_type = 'create_tenant'
  AND status = 'compensation_failed'
ORDER BY created_at DESC
LIMIT 10;
```

### Metrics

Track these KPIs:

- **Success rate**: `sagas passed / sagas executed`
- **Compensation rate**: `sagas compensated / sagas failed`
- **Dead-letter rate**: `failed compensations / sagas compensated`
- **Latency**: `p50, p95, p99` saga execution time

## Best Practices

1. **Keep steps small**: One operation per step (one DB write, one API call)
2. **Idempotency keys are mandatory**: Always generate UUIDs for retries
3. **Compensate order matters**: Undo in reverse (LIFO)
4. **Test compensation**: Don't just test the happy path
5. **Log everything**: Each step, each compensation, each failure
6. **Alert on dead-letters**: They require human intervention
7. **Document side effects**: If a step has external effects, document the undo

## References

- [Saga Pattern (Enterprise Integration Patterns)](https://microservices.io/patterns/data/saga.html)
- [Long-running Processes as Sagas](https://www.pulumi.com/blog/saga-orchestration-for-microservices/)
