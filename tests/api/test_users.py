import pytest
from unittest.mock import MagicMock
import uuid

from app.models.user import User, UserRole
from app.core import security

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_read_users_me_success(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id, 
        email="test@example.com", 
        role=UserRole.CANDIDATE, 
        is_active=True
    )
    
    # Create valid access token
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    # Mock get_current_user dependency's db call
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.return_value = mock_result
    
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["id"] == str(user_id)
    assert data["role"] == "CANDIDATE"

@pytest.mark.asyncio
async def test_read_users_me_invalid_token(async_client):
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"

@pytest.mark.asyncio
async def test_read_users_admin(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="admin@example.com", role=UserRole.ADMIN, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "ADMIN"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_users_res = MagicMock()
    mock_users_res.scalars().all.return_value = [user]
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_users_res]
    
    response = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    assert len(response.json()) == 1

@pytest.mark.asyncio
async def test_read_users_unauthorized(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="candidate@example.com", role=UserRole.CANDIDATE, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_db_session.execute.side_effect = [mock_user_res]
    
    response = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 403
