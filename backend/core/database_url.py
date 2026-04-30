"""Database URL helpers for runtime and migration engines."""

from sqlalchemy.engine import make_url


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
