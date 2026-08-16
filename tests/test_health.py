"""Tests for GET /health endpoint — DB and ORS reachability probes (Slice 4).

In the test environment neither a real DB nor an ORS instance is available,
so probes fail and the endpoint returns 503 by default.  We also exercise
the 200-ok path by mocking the internal helpers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from office_hero.api.app import app

client = TestClient(app)


class TestHealthResponseShape:
    """Verify the /health response always contains the three required fields."""

    def test_response_has_status_field(self):
        resp = client.get("/health")
        assert "status" in resp.json()

    def test_response_has_db_field(self):
        resp = client.get("/health")
        assert "db" in resp.json()

    def test_response_has_ors_field(self):
        resp = client.get("/health")
        assert "ors" in resp.json()

    def test_status_code_is_200_or_503(self):
        """Must only return 200 (healthy) or 503 (unhealthy)."""
        resp = client.get("/health")
        assert resp.status_code in (200, 503)

    def test_no_auth_required(self):
        """Health endpoint must be reachable without a JWT."""
        resp = client.get("/health")
        # Not 401 or 403
        assert resp.status_code not in (401, 403)


class TestHealthUnhealthyPaths:
    """Verify 503 is returned when DB or ORS is unreachable."""

    def test_db_unreachable_returns_503(self):
        """Without a real DB configured, db probe fails → 503."""
        resp = client.get("/health")
        body = resp.json()
        # In test env there is no engine/DB, so db must be 'error'
        assert body["db"] == "error"
        assert resp.status_code == 503

    def test_ors_unreachable_returns_503(self):
        """Without a real ORS service, ors probe fails → 503."""
        resp = client.get("/health")
        body = resp.json()
        assert body["ors"] == "error"
        assert resp.status_code == 503

    def test_status_is_unhealthy_when_db_down(self):
        resp = client.get("/health")
        assert resp.json()["status"] == "unhealthy"


class TestHealthHealthyPath:
    """Verify 200 is returned when both DB and ORS are healthy (mocked)."""

    def test_returns_200_when_both_probes_pass(self):
        """Mock engine + httpx so both probes succeed; expect 200 status=ok."""
        mock_engine = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_httpx_cm = AsyncMock()
        mock_httpx_cm.__aenter__ = AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=mock_response)))
        mock_httpx_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("office_hero.api.routes.health.get_engine", return_value=mock_engine),
            patch("office_hero.api.routes.health.get_session", return_value=mock_cm),
            patch("httpx.AsyncClient", return_value=mock_httpx_cm),
        ):
            resp = client.get("/health")

        body = resp.json()
        assert resp.status_code == 200
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["ors"] == "ok"

    def test_db_ok_ors_error_returns_503(self):
        """When DB passes but ORS fails, overall status is unhealthy (503)."""
        mock_engine = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("office_hero.api.routes.health.get_engine", return_value=mock_engine),
            patch("office_hero.api.routes.health.get_session", return_value=mock_cm),
            # ORS is unreachable (default — no httpx mock)
        ):
            resp = client.get("/health")

        body = resp.json()
        assert resp.status_code == 503
        assert body["db"] == "ok"
        assert body["ors"] == "error"
        assert body["status"] == "unhealthy"
