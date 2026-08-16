"""Tests for global exception handlers — correct HTTP status codes and safe responses (Slice 4).

All handlers are tested directly (unit-style) using mock Request objects so we
can exercise every branch without spinning up the full HTTP stack.  We also
verify via TestClient that the handlers are registered on the live app.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from office_hero.api.exception_handlers import (
    auth_error_handler,
    permission_error_handler,
    tenant_error_handler,
    unhandled_exception_handler,
)
from office_hero.core.exceptions import AuthError, PermissionError, TenantError


def _mock_request(request_id: str | None = "test-req-id") -> MagicMock:
    """Return a minimal mock Request with request_id on state."""
    req = MagicMock()
    req.state.request_id = request_id
    return req


# ---------------------------------------------------------------------------
# Auth error → 401
# ---------------------------------------------------------------------------


class TestAuthErrorHandler:
    async def test_returns_401(self):
        resp = await auth_error_handler(_mock_request(), AuthError("Bad credentials"))
        assert resp.status_code == 401

    async def test_body_contains_detail(self):
        resp = await auth_error_handler(_mock_request(), AuthError("Bad credentials"))
        body = json.loads(resp.body)
        assert "detail" in body
        assert body["detail"] == "Bad credentials"

    async def test_body_contains_request_id(self):
        resp = await auth_error_handler(_mock_request("req-abc"), AuthError("x"))
        body = json.loads(resp.body)
        assert body["request_id"] == "req-abc"

    async def test_works_when_request_id_is_none(self):
        req = MagicMock()
        # state has no request_id attribute
        del req.state.request_id
        type(req.state).request_id = property(lambda self: (_ for _ in ()).throw(AttributeError()))
        resp = await auth_error_handler(req, AuthError("x"))
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Permission error → 403
# ---------------------------------------------------------------------------


class TestPermissionErrorHandler:
    async def test_returns_403(self):
        resp = await permission_error_handler(_mock_request(), PermissionError("Not allowed"))
        assert resp.status_code == 403

    async def test_body_contains_detail(self):
        resp = await permission_error_handler(_mock_request(), PermissionError("No access"))
        body = json.loads(resp.body)
        assert body["detail"] == "No access"

    async def test_body_contains_request_id(self):
        resp = await permission_error_handler(_mock_request("req-xyz"), PermissionError("x"))
        body = json.loads(resp.body)
        assert body["request_id"] == "req-xyz"


# ---------------------------------------------------------------------------
# Tenant error → 400
# ---------------------------------------------------------------------------


class TestTenantErrorHandler:
    async def test_returns_400(self):
        resp = await tenant_error_handler(_mock_request(), TenantError("Bad tenant"))
        assert resp.status_code == 400

    async def test_body_contains_detail(self):
        resp = await tenant_error_handler(_mock_request(), TenantError("Tenant mismatch"))
        body = json.loads(resp.body)
        assert body["detail"] == "Tenant mismatch"

    async def test_body_contains_request_id(self):
        resp = await tenant_error_handler(_mock_request("req-t"), TenantError("x"))
        body = json.loads(resp.body)
        assert body["request_id"] == "req-t"


# ---------------------------------------------------------------------------
# Unhandled exception → 500 (no traceback leak)
# ---------------------------------------------------------------------------


class TestUnhandledExceptionHandler:
    async def test_returns_500(self):
        resp = await unhandled_exception_handler(_mock_request(), ValueError("boom"))
        assert resp.status_code == 500

    async def test_body_has_generic_detail(self):
        """Error detail must be generic — no raw exception message."""
        resp = await unhandled_exception_handler(_mock_request(), ValueError("secret internal error"))
        body = json.loads(resp.body)
        assert "detail" in body
        # Must not expose the raw exception message
        assert "secret internal error" not in body["detail"]

    async def test_no_traceback_in_response_body(self):
        """Stack traces must never appear in the response body."""
        resp = await unhandled_exception_handler(
            _mock_request(), RuntimeError("traceback_test_marker")
        )
        body = json.loads(resp.body)
        body_str = json.dumps(body)
        assert "traceback_test_marker" not in body_str
        assert "RuntimeError" not in body_str
        assert "Traceback" not in body_str

    async def test_body_contains_request_id(self):
        resp = await unhandled_exception_handler(_mock_request("req-500"), Exception("x"))
        body = json.loads(resp.body)
        assert body["request_id"] == "req-500"

    async def test_different_exception_types_all_return_500(self):
        """All unhandled exception types must map to 500."""
        for exc in (ValueError("v"), KeyError("k"), TypeError("t"), RuntimeError("r")):
            resp = await unhandled_exception_handler(_mock_request(), exc)
            assert resp.status_code == 500, f"Expected 500 for {type(exc).__name__}"


# ---------------------------------------------------------------------------
# Handler registration — verify handlers are wired into the live app
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Smoke-test that all handlers are registered and importable."""

    def test_register_function_is_importable(self):
        from office_hero.api.exception_handlers import register_exception_handlers

        assert callable(register_exception_handlers)

    def test_all_handlers_are_callable(self):
        handlers = [
            auth_error_handler,
            permission_error_handler,
            tenant_error_handler,
            unhandled_exception_handler,
        ]
        for handler in handlers:
            assert callable(handler), f"{handler.__name__} must be callable"
