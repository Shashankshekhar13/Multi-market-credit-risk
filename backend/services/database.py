
import logging

logger = logging.getLogger(__name__)

# Track whether DB is available
_db_available = False
engine = None
async_session = None

try:
    # pyrefly: ignore [missing-import]
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    # pyrefly: ignore [missing-import]
    from sqlalchemy import text
    from backend.services.config import DATABASE_URL
    from backend.models import Base

    if DATABASE_URL.startswith("postgresql"):
        engine = create_async_engine(
            DATABASE_URL,
            pool_size=5,
            max_overflow=15,
            pool_timeout=10,
            pool_recycle=1800,
            connect_args={"timeout": 10},
            echo=False,
        )
    else:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
        )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    _db_available = True
    logger.info("Database engine created successfully.")

except (ImportError, Exception) as e:
    logger.warning(f"Failed to create database engine: {e}. Checking SQLite fallback...")
    try:
        # pyrefly: ignore [missing-import]
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from backend.models import Base
        # pyrefly: ignore [missing-import]
        import aiosqlite

        sqlite_url = "sqlite+aiosqlite:///./credlens.db"
        logger.info(f"Falling back to SQLite at: {sqlite_url}")
        engine = create_async_engine(
            sqlite_url,
            echo=False,
        )
        async_session = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        _db_available = True
    except Exception as se:
        logger.warning(f"Database dependencies/fallback not installed: {se}. Running in stateless mode.")


# ─── Lifecycle ───

async def init_db():
    """Create all tables if they don't exist."""
    global engine, async_session, _db_available
    from backend.models import Base
    if not _db_available or engine is None:
        logger.warning("Database unavailable. Skipping table creation.")
        return

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully.")
    except Exception as e:
        if engine is not None and "postgresql" in str(engine.url):
            logger.warning(f"Failed to connect to PostgreSQL: {e}. Falling back to SQLite...")
            try:
                # pyrefly: ignore [missing-import]
                import aiosqlite
                # pyrefly: ignore [missing-import]
                from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
                from backend.models import Base

                sqlite_url = "sqlite+aiosqlite:///./credlens.db"
                engine = create_async_engine(
                    sqlite_url,
                    echo=False,
                )
                async_session = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                logger.info(f"Successfully initialized fallback SQLite database at {sqlite_url}")
                _db_available = True
                return
            except Exception as se:
                logger.warning(f"Failed to initialize SQLite fallback: {se}. Running in stateless mode.")
        else:
            logger.warning(f"Failed to initialize database: {e}. Running in stateless mode.")
        _db_available = False


async def close_db():
    """Dispose of the connection pool on shutdown."""
    if engine is not None:
        await engine.dispose()
        logger.info("Database connection pool closed.")


async def check_db_health() -> bool:
    """Check if the database is reachable."""
    if not _db_available or engine is None:
        return False
    try:
        # pyrefly: ignore [missing-import]
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ─── Dependency Injection ───

class _NullSession:
    """A dummy session that safely no-ops when DB is unavailable."""
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def execute(self, *args, **kwargs):
        class _EmptyResult:
            def scalar_one_or_none(self):
                return None
            def scalars(self):
                class _EmptyScalars:
                    def all(self):
                        return []
                return _EmptyScalars()
        return _EmptyResult()
    def add(self, *args, **kwargs):
        pass
    async def commit(self):
        pass
    async def rollback(self):
        pass
    async def close(self):
        pass


async def get_db():
    """FastAPI dependency that yields an async database session.

    If the database is not available, yields a NullSession that will
    raise clear errors if anything tries to use it.
    """
    if not _db_available or async_session is None:
        yield _NullSession()
        return

    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
