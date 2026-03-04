from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.settings import settings

# ── Primary (read-write) engine ───────────────────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Read replica engine (Phase 4) ────────────────────────────────────────────
# Falls back to the primary engine when DATABASE_REPLICA_URL is not set.

if settings.database_replica_url:
    _read_engine = create_async_engine(
        settings.database_replica_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )
    _read_session_maker = async_sessionmaker(_read_engine, class_=AsyncSession, expire_on_commit=False)
else:
    _read_engine = engine
    _read_session_maker = async_session_maker

Base = declarative_base()


async def get_db():
    """Primary database session — use for writes and strongly-consistent reads."""
    async with async_session_maker() as session:
        yield session


async def get_read_db():
    """
    Read-optimised database session.

    Routes to the read replica when DATABASE_REPLICA_URL is configured;
    falls back to the primary transparently when it is not.  Use this
    dependency on read-only endpoints (GET list/detail) to distribute
    query load in scaled deployments.
    """
    async with _read_session_maker() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
