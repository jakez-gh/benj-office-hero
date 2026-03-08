import pytest

from office_hero.db import engine as engine_mod
from office_hero.db import rls
from office_hero.db import session as session_mod


def test_create_async_engine_from_env(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        engine_mod.create_async_engine()

    # ensure the factory delegates to the underlying SQLAlchemy helper
    fake_info = {}

    def fake_create(url, **kwargs):
        fake_info["url"] = url
        fake_info["kwargs"] = kwargs
        return "dummy-engine"

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user@host/db")
    monkeypatch.setattr(engine_mod, "_create_async_engine", fake_create)

    eng = engine_mod.create_async_engine()
    assert eng == "dummy-engine"
    assert fake_info["url"] == "postgresql+asyncpg://user@host/db"


def test_enable_rls_and_tenant_column():
    sql = rls.enable_rls("foo_table")
    assert "ALTER TABLE foo_table ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY tenant_isolation" in sql

    col = rls.tenant_id_column()
    # inspect properties
    assert col.name == "tenant_id"
    assert str(col.type).startswith("UUID")
    assert not col.nullable


def test_get_session_monkeypatched(monkeypatch):
    # ensure get_session forwards to async_sessionmaker and yields a session
    class DummySession:
        pass

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    def fake_maker(engine, **kwargs):
        # verify engine is passed through
        assert engine is dummy_engine
        assert kwargs.get("expire_on_commit") is False
        # return a callable that will provide our context manager
        return lambda: DummyCtx()

    dummy_engine = object()
    monkeypatch.setattr(session_mod, "async_sessionmaker", fake_maker)

    async def runner():
        async with session_mod.get_session(dummy_engine) as sess:
            assert isinstance(sess, DummySession)

    import asyncio

    asyncio.run(runner())


def test_get_session_sets_tenant(monkeypatch):
    # verify that providing tenant_id causes a SET LOCAL statement
    executed = []

    class DummySession:
        async def execute(self, sql):
            executed.append(sql)

    class DummyCtx:
        async def __aenter__(self):
            return DummySession()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    def fake_maker(engine, **kwargs):
        return lambda: DummyCtx()

    dummy_engine = object()
    monkeypatch.setattr(session_mod, "async_sessionmaker", fake_maker)

    async def runner():
        async with session_mod.get_session(dummy_engine, tenant_id="foo"):
            # nothing to do inside; setup should have run already
            pass

    import asyncio

    asyncio.run(runner())
    assert executed, "no SQL was executed"
    assert "SET LOCAL app.tenant_id" in executed[0]
