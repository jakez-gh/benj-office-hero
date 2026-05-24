"""Tests for 429 rate limit response format — TDD first (Slice 4).

Verifies that rate-limited responses include proper headers and body
so clients can display user-friendly feedback.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from office_hero.api.app import app


def _client() -> TestClient:
    return TestClient(app)


class TestRateLimitResponseFormat:
    """Rate-limited (429) responses must include actionable data."""

    def test_rate_limit_error_handler_is_registered(self):
        """The custom 429 handler must be importable and callable."""
        from office_hero.api.exception_handlers import rate_limit_error_handler

        assert callable(rate_limit_error_handler)

    def test_rate_limit_error_handler_returns_429_with_retry_after(self):
        """Verify the 429 handler produces proper JSON body + header."""
        import asyncio
        import json
        from unittest.mock import MagicMock

        from slowapi.errors import RateLimitExceeded

        from office_hero.api.exception_handlers import rate_limit_error_handler

        mock_request = MagicMock()
        mock_request.state.request_id = "test-req-id"
        mock_request.url.path = "/auth/login"

        mock_limit = MagicMock()
        mock_limit.error_message = "Rate limit exceeded"
        exc = RateLimitExceeded(mock_limit)

        resp = asyncio.new_event_loop().run_until_complete(
            rate_limit_error_handler(mock_request, exc)
        )
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        body = json.loads(resp.body)
        assert "detail" in body
        assert body["retry_after"] == 60


class TestSecurityHeadersPresent:
    """All responses must include OWASP security headers."""

    def test_health_has_security_headers(self):
        """GET /health must include all 5 security headers."""
        client = _client()
        resp = client.get("/health")
        # Security headers middleware should apply to all responses
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert "default-src" in resp.headers.get("Content-Security-Policy", "")
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        # HSTS only in prod, but middleware always adds it
        assert "max-age" in resp.headers.get("Strict-Transport-Security", "")
