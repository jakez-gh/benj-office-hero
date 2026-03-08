from sqlalchemy import text


def tenant_policy(table_name: str) -> str:
    return f"CREATE POLICY tenant_isolation ON {table_name} USING (tenant_id = current_setting('app.tenant_id')::uuid);"


def set_tenant(session, tenant_id: str) -> None:
    """Helper to set the tenant_id session variable manually."""
    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
