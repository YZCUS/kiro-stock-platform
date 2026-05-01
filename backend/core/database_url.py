"""Database URL helpers for runtime and migration engines."""

from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool


def _is_postgresql(drivername: str) -> bool:
    return drivername == "postgresql" or drivername.startswith("postgresql+")


def _is_transaction_pooler(host: str | None, port: int | None) -> bool:
    host = host or ""
    return port == 6543 or host.endswith(".pooler.supabase.com")


def _render(url) -> str:
    return url.render_as_string(hide_password=False)


def make_async_database_url(database_url: str) -> str:
    """Return an asyncpg URL safe for Supabase/PgBouncer transaction poolers."""
    url = make_url(database_url)
    if not _is_postgresql(url.drivername):
        return database_url

    query = dict(url.query)
    if "sslmode" in query and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")

    if _is_transaction_pooler(url.host, url.port):
        query.setdefault("prepared_statement_cache_size", "0")

    return _render(url.set(drivername="postgresql+asyncpg", query=query))


def make_async_connect_args(database_url: str) -> dict:
    """Return asyncpg connect args required by specific hosting targets."""
    url = make_url(database_url)
    if _is_postgresql(url.drivername) and _is_transaction_pooler(url.host, url.port):
        return {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
    return {}


def make_async_engine_kwargs(database_url: str) -> dict:
    """Return SQLAlchemy async engine kwargs for the target database URL."""
    url = make_url(database_url)
    kwargs = {"connect_args": make_async_connect_args(database_url)}
    if _is_postgresql(url.drivername) and _is_transaction_pooler(url.host, url.port):
        kwargs["poolclass"] = NullPool
    return kwargs


def make_sync_database_url(database_url: str) -> str:
    """Return a psycopg2 URL for Alembic and sync tooling."""
    url = make_url(database_url)
    if not _is_postgresql(url.drivername):
        return database_url

    query = dict(url.query)
    query.pop("prepared_statement_cache_size", None)
    if "ssl" in query and "sslmode" not in query:
        query["sslmode"] = query.pop("ssl")

    return _render(url.set(drivername="postgresql+psycopg2", query=query))
