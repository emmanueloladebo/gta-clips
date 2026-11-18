import os
import shutil
import tempfile
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from packages.shared.config import settings
from packages.shared.database import get_db
from packages.shared.models import Base, User, Streamer, CreatorPermission, Clip
from packages.shared.enums import PlatformType, PermissionStatus, ApprovalStatus
from apps.api.main import app
from apps.api.auth import get_password_hash, create_access_token

# Test in-memory SQLite database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession) -> dict:
    stmt = select(User).where(User.username == "testadmin")
    existing_user = (await db_session.execute(stmt)).scalar_one_or_none()
    if not existing_user:
        existing_user = User(
            username="testadmin",
            email="testadmin@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_admin=True,
        )
        db_session.add(existing_user)
        await db_session.commit()
        await db_session.refresh(existing_user)

    token = create_access_token(data={"sub": existing_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_session_factory(db_session: AsyncSession):
    """Context manager factory for patching AsyncSessionLocal in tests."""
    @asynccontextmanager
    async def _factory():
        yield db_session

    return _factory


@pytest.fixture
def temp_scratch():
    temp_dir = tempfile.mkdtemp(prefix="test_scratch_")
    old_scratch = settings.SCRATCH_DIR
    settings.SCRATCH_DIR = temp_dir
    yield Path(temp_dir)
    settings.SCRATCH_DIR = old_scratch
    shutil.rmtree(temp_dir, ignore_errors=True)
