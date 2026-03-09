"""Helpers for generating Row-Level Security (RLS) helpers.

These utilities are primarily intended for use inside Alembic migrations.  At
this stage they are simple stubs that may grow as the schema evolves.
"""

import sqlalchemy as sa

# Whitelist of tables allowed for RLS policy creation to prevent SQL injection
_ALLOWED_TABLES = {"users", "refresh_tokens", "audit_events", "rate_limits", "ban_list"}


def enable_rls(table_name: str) -> str:
    """Return a SQL string that enables tenant-isolation RLS on ``table_name``.

    The returned fragment can be executed inside an Alembic upgrade script.

    Args:
        table_name: Name of the table (must be in _ALLOWED_TABLES whitelist).

    Raises:
        ValueError: If table_name is not in the whitelist.
    """
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(
            f"Table {table_name!r} is not whitelisted for RLS policy creation. "
            f"Allowed tables: {_ALLOWED_TABLES}"
        )

    return f"""
    ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON {table_name}
        USING (tenant_id = current_setting('app.tenant_id')::uuid);
    """


def tenant_id_column() -> sa.Column:
    """Convenience factory for a tenant_id column suitable for most tables.

    Downstream migrations can do::

        op.add_column('foo', tenant_id_column())
    """

    return sa.Column("tenant_id", sa.UUID(), nullable=False)
