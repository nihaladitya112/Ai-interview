import pytest
import uuid
from unittest.mock import MagicMock, patch

from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile
from app.core import security
from app.models.recommendation import Recommendation

@pytest.mark.asyncio
async def test_generate_recommendation_endpoint(async_client, mock_db_session):
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    profile = CandidateProfile(id=profile_id, user_id=user_id)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_profile_res = MagicMock()
    mock_profile_res.scalar_one_or_none.return_value = profile
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_profile_res]
    
    with patch("app.api.v1.recommendations.generate_learning_path") as mock_generate:
        from datetime import datetime, timezone
        rec = Recommendation(
            id=uuid.uuid4(),
            candidate_id=profile_id,
            missing_skills=["System Design"],
            learning_topics=["Deep dive into System Design"],
            prerequisites=[],
            practice_problems=[],
            project_recommendations=[],
            learning_sequence=[],
            created_at=datetime.now(timezone.utc)
        )
        mock_generate.return_value = rec
        
        response = await async_client.post(
            "/api/v1/recommendations/generate",
            json={"interview_id": str(interview_id)},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
    assert response.status_code == 201
    assert "System Design" in response.json()["missing_skills"]

@pytest.mark.asyncio
async def test_generate_recommendation_no_profile(async_client, mock_db_session):
    user_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_profile_res = MagicMock()
    mock_profile_res.scalar_one_or_none.return_value = None
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_profile_res]
    
    response = await async_client.post(
        "/api/v1/recommendations/generate",
        json={"interview_id": str(interview_id)},
        headers={"Authorization": f"Bearer {access_token}"}
    )
        
    assert response.status_code == 404
