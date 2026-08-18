import pytest
from unittest.mock import MagicMock, patch
import uuid
import json

from app.models.user import User, UserRole
from app.models.resume import Resume, FileType
from app.core import security

@pytest.mark.asyncio
@patch("app.worker.process_resume_task.delay")
async def test_upload_resume(mock_delay, async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id, 
        email="test@example.com", 
        role=UserRole.CANDIDATE, 
        is_active=True
    )
    
    mock_task = MagicMock()
    mock_task.id = "mock_task_id"
    mock_delay.return_value = mock_task
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user
    
    mock_profile_result = MagicMock()
    mock_profile_result.scalar_one_or_none.return_value = None
    
    mock_db_session.execute.side_effect = [mock_user_result, mock_profile_result, mock_profile_result]
    
    files = {"file": ("resume.txt", b"Test resume content", "text/plain")}
    response = await async_client.post(
        "/api/v1/resumes",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 201
    assert "task_id" in response.json()
    assert response.json()["task_id"] == "mock_task_id"
    assert response.json()["status"] == "processing"

@pytest.mark.asyncio
async def test_upload_resume_invalid_mime_type(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.side_effect = [mock_user_result, MagicMock()]
    
    files = {"file": ("script.py", b"print('hello')", "text/x-python")}
    response = await async_client.post(
        "/api/v1/resumes",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 415

@pytest.mark.asyncio
async def test_upload_resume_file_too_large(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user
    mock_db_session.execute.side_effect = [mock_user_result, MagicMock()]
    
    # 5MB + 1 byte
    large_content = b"0" * ((5 * 1024 * 1024) + 1)
    files = {"file": ("large.txt", large_content, "text/plain")}
    response = await async_client.post(
        "/api/v1/resumes",
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 413

@pytest.mark.asyncio
async def test_get_parsed_resume(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(
        id=user_id, 
        email="test@example.com", 
        role=UserRole.CANDIDATE, 
        is_active=True
    )
    
    resume_id = uuid.uuid4()
    parsed_data = {"Name": "Test Name", "Skills": ["Python"]}
    resume = Resume(
        id=resume_id,
        candidate_id=user_id,
        file_path="uploads/resumes/resume.txt",
        file_type=FileType.TXT,
        parsed_data=parsed_data
    )
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user
    
    mock_resume_result = MagicMock()
    mock_resume_result.scalar_one_or_none.return_value = resume
    
    mock_db_session.execute.side_effect = [mock_user_result, mock_resume_result]
    
    response = await async_client.get(
        f"/api/v1/resumes/{resume_id}/parsed",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json() == parsed_data
