"""
Async Database Session & Engine Configuration.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from packages.shared.config import settings
from packages.shared.models import Base

# Configure database engine based on DATABASE_URL
database_url = settings.DATABASE_URL

# For SQLite, ensure directory exists
if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        connect_args=connect_args,
    )
else:
    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
