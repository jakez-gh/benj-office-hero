from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID

# Tables approved for RLS enablement — add entries here when new tenant-isolated
# tables are introduced rather than allowing arbitrary DDL.
_WHITELISTED_TABLES: frozenset[str] = frozenset(
    {
        "users",
        "tenants",
        "refresh_tokens",
        "audit_events",
        "job_entries",
    }
)


def enable_rls(table_name: str) -> str:
    """Return DDL statements to enable row-level security on *table_name*.

    Raises:
        ValueError: If *table_name* is not in the whitelist, preventing
            accidental or malicious RLS enablement on arbitrary tables.
    """
    if table_name not in _WHITELISTED_TABLES:
        raise ValueError(
            f"Table '{table_name}' is not whitelisted for RLS enablement. "
            "Add it to _WHITELISTED_TABLES in office_hero/db/rls.py."
        )
    return (
        f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;\n"
        f"CREATE POLICY tenant_isolation ON {table_name} "
        f"USING (tenant_id = current_setting('app.tenant_id')::uuid);"
    )


def tenant_id_column() -> Column:  # type: ignore[type-arg]
    """Return a SQLAlchemy Column definition for the standard tenant FK column."""
    return Column("tenant_id", PGUUID(as_uuid=True), nullable=False)


# Whitelist of tables allowed for RLS policy creation to prevent SQL injection
_ALLOWED_TABLES = {"users", "refresh_tokens", "audit_events", "ban_list", "rate_limits"}

# Whitelist of tables allowed for RLS policy creation to prevent SQL injection
_ALLOWED_TABLES = {"users", "refresh_tokens", "audit_events", "ban_list", "rate_limits"}


def tenant_policy(table_name: str) -> str:
    """Generate a CREATE POLICY statement for tenant isolation.

    Args:
        table_name: Name of the table (must be in whitelist to prevent SQL injection).

    Returns:
        SQL string for creating a tenant isolation policy.

    Raises:
        ValueError: If table_name is not in the whitelist.
    """
    if table_name not in _ALLOWED_TABLES:
        raise ValueError(
            f"Table '{table_name}' not allowed for RLS policy creation. "
            f"Allowed tables: {_ALLOWED_TABLES}"
        )
    return f"CREATE POLICY tenant_isolation ON {table_name} USING (tenant_id = current_setting('app.tenant_id')::uuid);"


def set_tenant(session, tenant_id: str) -> None:
    """Helper to set the tenant_id session variable manually."""
    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
