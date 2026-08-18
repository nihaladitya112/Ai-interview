import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock redis and fastapi_limiter before importing app
sys.modules['redis'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['fastapi_limiter'] = MagicMock()

from fastapi import Request

class MockRateLimiter:
    def __init__(self, *args, **kwargs):
        pass
    async def __call__(self, request: Request):
        pass

mock_depends = MagicMock()
mock_depends.RateLimiter = MockRateLimiter
sys.modules['fastapi_limiter.depends'] = mock_depends

from app.main import app
from app.core.database import get_db


@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    # SQLAlchemy Session.add() and Session.flush() are synchronous —
    # configure the mock so they return None synchronously, preventing
    # the "coroutine was never awaited" RuntimeWarning.
    session.add = MagicMock(return_value=None)
    session.flush = AsyncMock(return_value=None)
    return session


@pytest.fixture
def override_get_db(mock_db_session):
    async def _override_get_db():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
