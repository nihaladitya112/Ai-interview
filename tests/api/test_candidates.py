import pytest
import uuid
from unittest.mock import MagicMock

from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile
from app.models.recommendation import Recommendation
from app.core import security

@pytest.mark.asyncio
async def test_get_candidate_skills(async_client, mock_db_session):
    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    profile = CandidateProfile(id=candidate_id, user_id=user_id)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_profile_res = MagicMock()
    mock_profile_res.scalar_one_or_none.return_value = profile
    
    mock_skills_res = MagicMock()
    # Mock returning tuples of (CandidateSkill, Skill)
    class MockSkill:
        id = uuid.uuid4()
        name = "Python"
        category = "Backend"
    class MockCandSkill:
        proficiency_score = 8.5
    mock_skills_res.all.return_value = [(MockCandSkill(), MockSkill())]
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_profile_res, mock_skills_res]
    
    response = await async_client.get(
        f"/api/v1/candidates/{candidate_id}/skills",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Python"
    assert data[0]["proficiency_score"] == 8.5

@pytest.mark.asyncio
async def test_get_candidate_recommendations(async_client, mock_db_session):
    user_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    from datetime import datetime, timezone
    rec = Recommendation(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        missing_skills=["Kubernetes"],
        learning_topics=[],
        prerequisites=[],
        practice_problems=[],
        project_recommendations=[],
        learning_sequence=[],
        created_at=datetime.now(timezone.utc)
    )
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_recs_res = MagicMock()
    mock_recs_res.scalars().all.return_value = [rec]
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_recs_res]
    
    response = await async_client.get(
        f"/api/v1/candidates/{candidate_id}/recommendations",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Kubernetes" in data[0]["missing_skills"]
