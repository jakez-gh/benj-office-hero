from uuid import uuid4

import pytest

from office_hero.adapters.back_office import Customer
from office_hero.services.back_office_service import BackOfficeService


class RecordingAdapter:
    def __init__(self):
        self.calls = []
        self.customers = {}

    async def health_check(self) -> bool:
        return True

    async def get_customer(self, id):
        self.calls.append(("get_customer", id))
        return self.customers.get(id)

    async def create_customer(self, customer):
        self.calls.append(("create_customer", customer))
        self.customers[customer.id] = customer
        return customer

    async def update_customer(self, customer):
        self.calls.append(("update_customer", customer))
        self.customers[customer.id] = customer
        return customer

    async def delete_customer(self, id):
        self.calls.append(("delete_customer", id))
        self.customers.pop(id, None)

    async def get_job(self, id):
        self.calls.append(("get_job", id))
        return None

    async def create_job(self, job):
        self.calls.append(("create_job", job))
        return job

    async def update_job(self, job):
        self.calls.append(("update_job", job))
        return job

    async def delete_job(self, id):
        self.calls.append(("delete_job", id))


@pytest.mark.asyncio
async def test_upsert_customer_creates_when_missing():
    adapter = RecordingAdapter()
    svc = BackOfficeService(adapter)
    cid = uuid4()
    cust = Customer(id=cid, name="alice")
    result = await svc.upsert_customer(cust)
    assert result is cust
    assert ("create_customer", cust) in adapter.calls


@pytest.mark.asyncio
async def test_upsert_customer_updates_when_present():
    adapter = RecordingAdapter()
    cid = uuid4()
    existing = Customer(id=cid, name="bob")
    adapter.customers[cid] = existing
    svc = BackOfficeService(adapter)
    new = Customer(id=cid, name="bobby")
    result = await svc.upsert_customer(new)
    assert result is new
    assert ("update_customer", new) in adapter.calls
