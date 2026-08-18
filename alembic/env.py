from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so that autogenerate picks them up
import app.models  # noqa: F401, E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Derive a *synchronous* DB URL from settings.
# Alembic runs migrations synchronously; asyncpg cannot be used here.
# We swap  postgresql+asyncpg://  →  postgresql+psycopg://
# (psycopg v3 is already in requirements.txt as psycopg[binary])
# ---------------------------------------------------------------------------
_async_url: str = settings.DATABASE_URI or (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
SYNC_DB_URL: str = _async_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

config.set_main_option("sqlalchemy.url", SYNC_DB_URL)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database.

    Useful for generating a SQL script that can be applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
