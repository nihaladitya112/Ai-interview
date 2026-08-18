import pytest
from unittest.mock import MagicMock, patch
import uuid

from app.models.job import Job
from app.models.user import User, UserRole
from app.core import security

@pytest.mark.asyncio
async def test_create_job(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="admin@example.com", role=UserRole.ADMIN, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "ADMIN"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    mock_db_session.execute.side_effect = [mock_user_res]
    
    payload = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "description": "We are looking for a Python dev."
    }

    with patch("app.api.v1.jobs.process_job") as mock_process:
        mock_process.return_value = Job(
            id=uuid.uuid4(),
            title="Backend Developer",
            description="We are looking for a Python dev.",
            company="Tech Corp",
            required_skills=["Python"]
        )
        response = await async_client.post(
            "/api/v1/jobs",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    # The title should be overridden by the mock LLM which returns "Backend Developer"
    assert data["title"] == "Backend Developer" 
    assert data["company"] == "Tech Corp"
    assert "Python" in data["required_skills"]

@pytest.mark.asyncio
async def test_get_job(async_client, mock_db_session):
    user_id = uuid.uuid4()
    user = User(id=user_id, email="candidate@example.com", role=UserRole.CANDIDATE, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        title="Software Engineer",
        description="Great job",
        company="Tech Corp"
    )

    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_job_res = MagicMock()
    mock_job_res.scalar_one_or_none.return_value = job
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_job_res]

    response = await async_client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["id"] == str(job_id)
    assert response.json()["title"] == "Software Engineer"

@pytest.mark.asyncio
async def test_create_job_unauthorized(async_client, mock_db_session):
    user_id = uuid.uuid4()
    # Candidate should not be allowed to create a job
    user = User(id=user_id, email="candidate@example.com", role=UserRole.CANDIDATE, is_active=True)
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    mock_db_session.execute.side_effect = [mock_user_res]
    
    payload = {
        "title": "Software Engineer",
        "company": "Tech Corp",
        "description": "We are looking for a Python dev."
    }
    
    response = await async_client.post(
        "/api/v1/jobs",
        json=payload,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 403
