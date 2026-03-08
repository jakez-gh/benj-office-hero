"""Helpers for generating Row-Level Security (RLS) helpers.

These utilities are primarily intended for use inside Alembic migrations.  At
this stage they are simple stubs that may grow as the schema evolves.
"""

import sqlalchemy as sa


def enable_rls(table_name: str) -> str:
    """Return a SQL string that enables tenant-isolation RLS on ``table_name``.

    The returned fragment can be executed inside an Alembic upgrade script.
    """

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
