"""Tests for RateLimitManager — 100% branch coverage (ADR 007, Slice 4)."""

from __future__ import annotations

import time

from office_hero.services.rate_limit_manager import _DEFAULTS, RateLimitManager


class TestRateLimitManagerInstanceIsolation:
    """Verify that each instance has its own independent cache (SOLID/DI rule)."""

    def test_separate_instances_have_independent_caches(self):
        """Two RateLimitManager instances must not share cache state."""
        mgr_a = RateLimitManager()
        mgr_b = RateLimitManager()

        # Prime mgr_a's cache
        mgr_a.get_limit("auth")

        # mgr_b should have an empty cache (no shared state)
        assert mgr_b._cache == {}

    def test_cache_is_initialised_empty_on_construction(self):
        """self._cache must start as an empty dict."""
        mgr = RateLimitManager()
        assert mgr._cache == {}


class TestGetLimit:
    """Tests for RateLimitManager.get_limit()."""

    def test_known_scope_returns_correct_default(self):
        """'auth' scope must return the hard-coded default of 10."""
        mgr = RateLimitManager()
        assert mgr.get_limit("auth") == _DEFAULTS["auth"]

    def test_write_scope(self):
        assert RateLimitManager().get_limit("write") == _DEFAULTS["write"]

    def test_read_scope(self):
        assert RateLimitManager().get_limit("read") == _DEFAULTS["read"]

    def test_global_scope(self):
        assert RateLimitManager().get_limit("global") == _DEFAULTS["global"]

    def test_unknown_scope_falls_back_to_global(self):
        """An unrecognised scope must fall back to the 'global' default."""
        mgr = RateLimitManager()
        assert mgr.get_limit("unknown_scope_xyz") == _DEFAULTS["global"]

    def test_scope_is_case_normalised(self):
        """Scope lookup must be case-insensitive."""
        mgr = RateLimitManager()
        assert mgr.get_limit("AUTH") == mgr.get_limit("auth")

    def test_cache_hit_returns_same_value(self):
        """Second call for same scope must be served from cache."""
        mgr = RateLimitManager()
        first = mgr.get_limit("auth")
        second = mgr.get_limit("auth")
        assert first == second

    def test_cache_stores_value(self):
        """After get_limit(), the value must be present in self._cache."""
        mgr = RateLimitManager()
        mgr.get_limit("auth")
        assert "limit:auth" in mgr._cache

    def test_expired_cache_entry_is_not_returned(self, monkeypatch):
        """A TTL-expired cache entry must not be returned; a fresh lookup occurs."""
        mgr = RateLimitManager()
        # Populate cache with a stale entry (expiry in the past)
        mgr._cache["limit:auth"] = (999, time.monotonic() - 10.0)
        # Should re-fetch from defaults, not return stale 999
        result = mgr.get_limit("auth")
        assert result == _DEFAULTS["auth"]
        assert result != 999


class TestIsBanned:
    """Tests for RateLimitManager.is_banned()."""

    def test_not_banned_by_default(self):
        """is_banned() must return False for any key when no DB is configured."""
        mgr = RateLimitManager()
        assert mgr.is_banned("tenant:abc") is False

    def test_is_banned_cache_hit(self):
        """Second call for same key must be served from cache."""
        mgr = RateLimitManager()
        first = mgr.is_banned("tenant:abc")
        second = mgr.is_banned("tenant:abc")
        assert first == second is False

    def test_is_banned_stores_result_in_cache(self):
        """After is_banned(), the result must be in self._cache."""
        mgr = RateLimitManager()
        mgr.is_banned("tenant:abc")
        assert "ban:tenant:abc" in mgr._cache

    def test_expired_ban_cache_is_not_returned(self):
        """A TTL-expired ban cache entry must not be returned."""
        mgr = RateLimitManager()
        # Inject a stale 'True' ban entry
        mgr._cache["ban:tenant:abc"] = (True, time.monotonic() - 10.0)
        # Should re-evaluate (default: False)
        result = mgr.is_banned("tenant:abc")
        assert result is False


class TestSlowapiLimitString:
    """Tests for RateLimitManager.slowapi_limit_string()."""

    def test_returns_correct_format(self):
        """Must return '<limit>/minute' format for a known scope."""
        mgr = RateLimitManager()
        result = mgr.slowapi_limit_string("auth")
        assert result == f"{_DEFAULTS['auth']}/minute"

    def test_unknown_scope_uses_global_fallback(self):
        """Unknown scope must use global default in slowapi string."""
        mgr = RateLimitManager()
        result = mgr.slowapi_limit_string("nonexistent")
        assert result == f"{_DEFAULTS['global']}/minute"


class TestCacheHelpers:
    """Direct unit tests for _cache_get / _cache_set private helpers."""

    def test_cache_miss_returns_none(self):
        """_cache_get on a cold cache must return None."""
        mgr = RateLimitManager()
        assert mgr._cache_get("missing_key") is None

    def test_cache_set_then_get(self):
        """Value stored via _cache_set must be retrievable via _cache_get."""
        mgr = RateLimitManager()
        mgr._cache_set("mykey", 42)
        assert mgr._cache_get("mykey") == 42

    def test_expired_entry_returns_none(self):
        """_cache_get must return None for an expired entry."""
        mgr = RateLimitManager()
        mgr._cache["mykey"] = (42, time.monotonic() - 5.0)
        assert mgr._cache_get("mykey") is None
