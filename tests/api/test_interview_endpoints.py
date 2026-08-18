import pytest
import uuid
from unittest.mock import MagicMock, patch

from app.models.user import User, UserRole
from app.models.interview import Interview, InterviewStatus
from app.models.candidate import CandidateProfile
from app.core import security
from app.schemas.interview import InterviewStateResponse, CurrentQuestionInfo

@pytest.mark.asyncio
async def test_start_existing_interview_endpoint(async_client, mock_db_session):
    user_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    interview = Interview(id=interview_id, status=InterviewStatus.NOT_STARTED, total_questions=5)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_int_res = MagicMock()
    mock_int_res.scalar_one_or_none.return_value = interview
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_int_res]
    
    with patch("app.api.v1.interview.start_interview") as mock_start:
        mock_state = InterviewStateResponse(
            interview_id=str(interview_id),
            status=InterviewStatus.TECHNICAL,
            current_question=None,
            current_difficulty="MEDIUM",
            questions_asked=1,
            total_questions=5,
            skill_scores={},
            overall_score=0.0,
            conversation_history=[]
        )
        mock_start.return_value = mock_state
        
        response = await async_client.post(
            f"/api/v1/interviews/{interview_id}/start",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
    assert response.status_code == 200
    assert response.json()["status"] == "TECHNICAL"

@pytest.mark.asyncio
async def test_finish_interview_endpoint(async_client, mock_db_session):
    user_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    interview = Interview(id=interview_id, status=InterviewStatus.COMPLETED)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_int_res = MagicMock()
    mock_int_res.scalar_one_or_none.return_value = interview
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_int_res]
    
    with patch("app.worker.generate_interview_report_task.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "mock_report_task"
        mock_delay.return_value = mock_task
        
        response = await async_client.post(
            f"/api/v1/interviews/{interview_id}/finish",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
    assert response.status_code == 200
    assert response.json()["task_id"] == "mock_report_task"
    assert response.json()["status"] == "processing"

@pytest.mark.asyncio
async def test_get_report_not_ready(async_client, mock_db_session):
    user_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    
    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    interview = Interview(id=interview_id, status=InterviewStatus.COMPLETED)
    
    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})
    
    mock_user_res = MagicMock()
    mock_user_res.scalar_one_or_none.return_value = user
    
    mock_int_res = MagicMock()
    mock_int_res.scalar_one_or_none.return_value = interview
    
    mock_rep_res = MagicMock()
    mock_rep_res.scalar_one_or_none.return_value = None
    
    mock_db_session.execute.side_effect = [mock_user_res, mock_int_res, mock_rep_res]
    
    response = await async_client.get(
        f"/api/v1/interviews/{interview_id}/report",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 404
