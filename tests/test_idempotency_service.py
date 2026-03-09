"""Tests for idempotency service."""

from uuid import uuid4

import pytest

from office_hero.services.idempotency_service import IdempotencyService


def test_idempotency_service_store_and_retrieve():
    """IdempotencyService caches and retrieves step results."""
    svc = IdempotencyService()
    key = uuid4()
    result = {"customer_id": "123"}

    svc.store_result(key, "create_customer", result)

    cached = svc.get_cached_result(key, "create_customer")
    assert cached == result


def test_idempotency_service_miss():
    """IdempotencyService returns None for cache miss."""
    svc = IdempotencyService()
    key = uuid4()

    cached = svc.get_cached_result(key, "nonexistent_step")
    assert cached is None


def test_idempotency_service_key_reuse_across_steps():
    """IdempotencyService raises if the same key is used for different steps."""
    svc = IdempotencyService()
    key = uuid4()

    svc.store_result(key, "step_a", {"result": "a"})

    with pytest.raises(ValueError, match="used for step 'step_a'"):
        svc.get_cached_result(key, "step_b")


def test_idempotency_service_clear_cache():
    """IdempotencyService can clear all cached results."""
    svc = IdempotencyService()
    key1 = uuid4()
    key2 = uuid4()

    svc.store_result(key1, "step1", {"a": 1})
    svc.store_result(key2, "step2", {"b": 2})

    svc.clear_cache()

    assert svc.get_cached_result(key1, "step1") is None
    assert svc.get_cached_result(key2, "step2") is None


def test_idempotency_service_clear_specific_key():
    """IdempotencyService can clear a specific cached result."""
    svc = IdempotencyService()
    key1 = uuid4()
    key2 = uuid4()

    svc.store_result(key1, "step1", {"a": 1})
    svc.store_result(key2, "step2", {"b": 2})

    svc.clear_key(key1)

    assert svc.get_cached_result(key1, "step1") is None
    assert svc.get_cached_result(key2, "step2") == {"b": 2}
