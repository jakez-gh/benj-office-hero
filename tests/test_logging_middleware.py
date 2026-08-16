"""Tests for LoggingMiddleware — request context binding and lifecycle events (Slice 4).

Tests are behavioural: they verify the observable side-effects of the middleware
(X-Request-ID header, request_id uniqueness, passthrough of client-supplied IDs)
rather than testing internal structlog calls directly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from office_hero.api.app import app

client = TestClient(app)


class TestRequestIdHeader:
    """Verify the X-Request-ID response header behaviour."""

    def test_x_request_id_present_on_every_response(self):
        """Middleware must set X-Request-ID on all responses."""
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers

    def test_x_request_id_is_valid_uuid(self):
        """Auto-generated X-Request-ID must be a well-formed UUID."""
        resp = client.get("/health")
        request_id = resp.headers["X-Request-ID"]
        # Will raise ValueError if not a valid UUID
        UUID(request_id)

    def test_different_requests_get_unique_ids(self):
        """Each request must get its own unique X-Request-ID."""
        resp1 = client.get("/health")
        resp2 = client.get("/health")
        assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]

    def test_client_supplied_request_id_is_echoed(self):
        """If client sends X-Request-ID, the same value must be returned."""
        custom_id = str(uuid4())
        resp = client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["X-Request-ID"] == custom_id

    def test_invalid_client_request_id_is_replaced_with_uuid(self):
        """A non-UUID X-Request-ID from the client must be discarded and replaced."""
        resp = client.get("/health", headers={"X-Request-ID": "not-a-valid-uuid"})
        returned_id = resp.headers["X-Request-ID"]
        # Must be a valid UUID (not the invalid string)
        UUID(returned_id)
        assert returned_id != "not-a-valid-uuid"

    def test_request_id_applied_to_all_routes(self):
        """X-Request-ID must be set on any route, not just /health."""
        routes_to_check = [
            "/health",
            "/admin/audit-events",
        ]
        for path in routes_to_check:
            resp = client.get(path)
            assert "X-Request-ID" in resp.headers, f"Missing X-Request-ID on {path}"


class TestLoggingMiddlewareImport:
    """Verify LoggingMiddleware is importable and correctly structured."""

    def test_logging_middleware_is_importable(self):
        from office_hero.api.middleware.logging import LoggingMiddleware

        assert LoggingMiddleware is not None

    def test_logging_middleware_has_dispatch_method(self):
        from office_hero.api.middleware.logging import LoggingMiddleware

        assert callable(getattr(LoggingMiddleware, "dispatch", None))
