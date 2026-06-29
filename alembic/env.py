import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, event, pool
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

from alembic import context
from alembic.ddl.sqlite import SQLiteImpl

# Map PostgreSQL-only column types to their SQLite equivalents so migrations
# that use postgresql.JSONB, postgresql.ARRAY, etc. can still run locally
# against SQLite without changing the migration files.
SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
SQLiteTypeCompiler.visit_CITEXT = lambda self, type_, **kw: "TEXT"

# SQLite doesn't support ALTER TABLE ADD CONSTRAINT; FK checks are opt-in anyway.
# Turn add_constraint into a no-op when running against SQLite.
SQLiteImpl.add_constraint = lambda self, const: None

# Load .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get DATABASE_URL from environment
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Convert async driver URLs to sync equivalents for alembic
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from office_hero.models import Base  # noqa: E402

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


_NOOP = "SELECT 1 /* pg-only DDL skipped for sqlite */"

# Prefixes that are always PG-only (entire statement is skipped)
_PG_ONLY_PREFIXES = (
    "CREATE EXTENSION",
    "DROP EXTENSION",
    "CREATE OR REPLACE FUNCTION",
    "CREATE FUNCTION",
    "DROP FUNCTION",
    "CREATE TRIGGER",
    "DROP TRIGGER",
    "CREATE POLICY",
    "DROP POLICY",
    "DO $$",
    "DO\n$$",
)

# Substrings that, when found anywhere in the statement, mark it PG-only
_PG_ONLY_SUBSTRINGS = (
    "ENABLE ROW LEVEL SECURITY",
    "DISABLE ROW LEVEL SECURITY",
    "OWNER TO",
    "$$ LANGUAGE",
    "SET search_path",
    "LANGUAGE PLPGSQL",
    "RETURNS TRIGGER",
    "USING GIN",
    "USING BRIN",
    "USING GIST",
    "USING SPGIST",
    "gin_trgm_ops",
    "gist_trgm_ops",
    "_trgm_ops",
    "jsonb_path_ops",
    "current_setting(",
)


def _sqlite_skip_pg_ddl(conn, cursor, statement, parameters, context, executemany):
    """No-op PostgreSQL-specific DDL when running against SQLite."""
    upper = statement.upper().strip()
    if any(upper.startswith(kw.upper()) for kw in _PG_ONLY_PREFIXES):
        return _NOOP, parameters
    if any(kw.upper() in upper for kw in _PG_ONLY_SUBSTRINGS):
        return _NOOP, parameters
    return statement, parameters


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Build the configuration dict
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    # Use sync connection
    with connectable.connect() as connection:
        if connectable.dialect.name == "sqlite":
            event.listen(connection, "before_cursor_execute", _sqlite_skip_pg_ddl, retval=True)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connectable.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
