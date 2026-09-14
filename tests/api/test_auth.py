import pytest
from unittest.mock import MagicMock
import uuid
from datetime import datetime, timedelta, timezone

from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.core import security
from app.core.config import settings

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_register_success(async_client, mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # No existing user
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "role": "CANDIDATE"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "CANDIDATE"
    assert "id" in data

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_register_duplicate_email(async_client, mock_db_session):
    existing_user = User(email="test@example.com")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "role": "CANDIDATE"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

@pytest.mark.asyncio
async def test_login_success(async_client, mock_db_session):
    user_id = uuid.uuid4()
    hashed_pw = security.get_password_hash("password123")
    user = User(id=user_id, email="test@example.com", hashed_password=hashed_pw, role=UserRole.CANDIDATE)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client, mock_db_session):
    user_id = uuid.uuid4()
    hashed_pw = security.get_password_hash("password123")
    user = User(id=user_id, email="test@example.com", hashed_password=hashed_pw, role=UserRole.CANDIDATE)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_refresh_success(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, role=UserRole.CANDIDATE)
    
    # Generate valid refresh token
    refresh_token = security.create_refresh_token({"sub": str(user_id)})
    
    token_obj = RefreshToken(
        user_id=user_id,
        token=refresh_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        user=user
    )
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = token_obj
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.post(
        "/api/v1/auth/refresh",
        params={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
