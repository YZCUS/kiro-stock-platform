from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.settings import get_settings


def _is_postgresql(drivername: str) -> bool:
    return drivername == "postgresql" or drivername.startswith("postgresql+")


def _is_transaction_pooler(host: str | None, port: int | None) -> bool:
    host = host or ""
    return port == 6543 or host.endswith(".pooler.supabase.com")


def make_async_database_url(url: str) -> str:
    parsed = make_url(url)
    if not _is_postgresql(parsed.drivername):
        return url

    query = dict(parsed.query)
    if "sslmode" in query and "ssl" not in query:
        query["ssl"] = query.pop("sslmode")
    if _is_transaction_pooler(parsed.host, parsed.port):
        query.setdefault("prepared_statement_cache_size", "0")

    return parsed.set(drivername="postgresql+asyncpg", query=query).render_as_string(
        hide_password=False
    )


def make_async_engine_kwargs(
    url: str,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> dict:
    parsed = make_url(url)
    kwargs = {"connect_args": {}}
    if _is_postgresql(parsed.drivername) and _is_transaction_pooler(
        parsed.host, parsed.port
    ):
        kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        }
        kwargs["poolclass"] = NullPool
    elif pool_size is not None and max_overflow is not None:
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
    return kwargs


settings = get_settings()
engine = create_async_engine(
    make_async_database_url(settings.database_url),
    pool_pre_ping=True,
    future=True,
    **make_async_engine_kwargs(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    ),
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
