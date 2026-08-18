import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.interview import Interview, InterviewStatus
from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty
from app.services.interview_engine import start_interview, submit_answer, _sessions, InterviewSession

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session

@pytest.mark.asyncio
async def test_start_interview(mock_db_session):
    interview_id = uuid.uuid4()
    interview = Interview(
        id=interview_id,
        status=InterviewStatus.NOT_STARTED,
        total_questions=5
    )
    
    question = InterviewQuestion(
        id=uuid.uuid4(),
        interview_id=interview_id,
        question_text="Q1",
        category=QuestionCategory.TECHNICAL,
        difficulty=QuestionDifficulty.MEDIUM,
        sequence_number=1
    )
    
    # Mocking select results:
    # 1. select interview
    # 2. select questions
    mock_interview_result = MagicMock()
    mock_interview_result.scalar_one_or_none.return_value = interview
    
    mock_q_result = MagicMock()
    mock_q_result.scalars().all.return_value = [question]
    
    mock_db_session.execute.side_effect = [mock_interview_result, mock_q_result]
    
    # Reset session cache
    _sessions.clear()
    
    state = await start_interview(interview_id, mock_db_session)
    
    assert interview.status == InterviewStatus.TECHNICAL
    assert state.status == InterviewStatus.TECHNICAL
    assert state.current_question.question_id == str(question.id)
    assert mock_db_session.add.called
    assert mock_db_session.commit.called

@pytest.mark.asyncio
async def test_submit_answer(mock_db_session):
    interview_id = uuid.uuid4()
    interview = Interview(
        id=interview_id,
        status=InterviewStatus.TECHNICAL,
        total_questions=5
    )
    
    question = InterviewQuestion(
        id=uuid.uuid4(),
        interview_id=interview_id,
        question_text="Explain Python",
        category=QuestionCategory.TECHNICAL,
        difficulty=QuestionDifficulty.MEDIUM,
        sequence_number=1
    )
    
    _sessions.clear()
    session = InterviewSession(interview_id)
    session.current_question_id = question.id
    session.phase_question_count = 1
    _sessions[interview_id] = session
    
    # Mocks:
    # 1. select interview
    # 2. select current question
    # 3. retrieve context (RAG) -> return []
    # 4. _pick_next_question select query
    mock_int_res = MagicMock()
    mock_int_res.scalar_one_or_none.return_value = interview
    
    mock_q_res = MagicMock()
    mock_q_res.scalar_one_or_none.return_value = question
    
    mock_rag_res = MagicMock()
    mock_rag_res.scalars().all.return_value = []
    
    mock_next_q_res = MagicMock()
    mock_next_q_res.scalars().all.return_value = [] # No next questions
    
    mock_db_session.execute.side_effect = [mock_int_res, mock_q_res, mock_rag_res, mock_next_q_res]
    
    response = await submit_answer(interview_id, "Good answer text for Python", mock_db_session)
    
    assert response.evaluation is not None
    assert interview.status == InterviewStatus.COMPLETED
    assert mock_db_session.commit.called

@pytest.mark.asyncio
async def test_submit_answer_transitions_to_follow_up(mock_db_session):
    interview_id = uuid.uuid4()
    interview = Interview(
        id=interview_id,
        status=InterviewStatus.TECHNICAL,
        total_questions=5
    )
    
    question = InterviewQuestion(
        id=uuid.uuid4(),
        interview_id=interview_id,
        question_text="Explain Python",
        category=QuestionCategory.TECHNICAL,
        difficulty=QuestionDifficulty.MEDIUM,
        sequence_number=1
    )
    
    next_question = InterviewQuestion(
        id=uuid.uuid4(),
        interview_id=interview_id,
        question_text="Follow-up: decorators",
        category=QuestionCategory.TECHNICAL,
        difficulty=QuestionDifficulty.MEDIUM,
        sequence_number=2
    )
    
    _sessions.clear()
    session = InterviewSession(interview_id)
    session.current_question_id = question.id
    session.phase_question_count = 1
    _sessions[interview_id] = session
    
    mock_int_res = MagicMock()
    mock_int_res.scalar_one_or_none.return_value = interview
    mock_q_res = MagicMock()
    mock_q_res.scalar_one_or_none.return_value = question
    mock_rag_res = MagicMock()
    mock_rag_res.scalars().all.return_value = []
    mock_next_q_res = MagicMock()
    mock_next_q_res.scalars().all.return_value = [next_question]
    
    mock_db_session.execute.side_effect = [mock_int_res, mock_q_res, mock_rag_res, mock_next_q_res]
    
    # A short, weak answer that forces follow-up
    response = await submit_answer(interview_id, "Idk python decorators", mock_db_session)
    
    assert interview.status == InterviewStatus.FOLLOW_UP
    assert response.next_question.question_id == str(next_question.id)
    assert session.in_follow_up is True
