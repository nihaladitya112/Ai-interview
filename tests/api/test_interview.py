"""
Tests for Phase 8: AI Interview Engine

Unit tests cover the answer evaluator and session state machine.
Integration tests exercise the start → answer → state flow.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import uuid

from app.models.user import User, UserRole
from app.models.resume import Resume, FileType
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.interview import Interview, InterviewStatus
from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty
from app.core import security


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: Answer Evaluator
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Requires schema update")
def test_evaluate_long_answer_scores_higher():
    from app.ai.answer_evaluator import evaluate_answer
    short = evaluate_answer("Explain Python decorators.", "They wrap functions.", skill_tag="python")
    long = evaluate_answer(
        "Explain Python decorators.",
        "A decorator in Python is a callable that takes a function as an argument and extends "
        "its behavior without modifying it. Decorators use the @syntax and are commonly used for "
        "logging, authentication, caching, and more. For example, @functools.lru_cache is a "
        "decorator that adds memoization. Under the hood, a decorator replaces the original "
        "function with a wrapped version.",
        skill_tag="python",
    )
    assert long.overall_score > short.overall_score


@pytest.mark.skip(reason="Requires schema update")
def test_evaluate_returns_all_dimensions():
    from app.ai.answer_evaluator import evaluate_answer
    result = evaluate_answer("What is SQL?", "SQL is a language for databases.", skill_tag="sql")
    assert 0 <= result.technical_correctness <= 10
    assert 0 <= result.relevance <= 10
    assert 0 <= result.depth <= 10
    assert 0 <= result.reasoning <= 10
    assert 0 <= result.clarity <= 10
    assert 0 <= result.completeness <= 10
    assert isinstance(result.feedback, str)
    assert isinstance(result.strengths, list)
    assert isinstance(result.weaknesses, list)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: Interview Session state machine
# ─────────────────────────────────────────────────────────────────────────────

def test_session_adapt_difficulty_up():
    from app.services.interview_engine import InterviewSession, QuestionDifficulty
    from app.ai.answer_evaluator import EvaluationResult
    session = InterviewSession(uuid.uuid4())
    session.current_difficulty = QuestionDifficulty.MEDIUM
    session.record_and_adapt(EvaluationResult(overall_score=9.0), skill_tag="python")
    assert session.current_difficulty == QuestionDifficulty.HARD


def test_session_adapt_difficulty_down():
    from app.services.interview_engine import InterviewSession, QuestionDifficulty
    from app.ai.answer_evaluator import EvaluationResult
    session = InterviewSession(uuid.uuid4())
    session.current_difficulty = QuestionDifficulty.MEDIUM
    session.record_and_adapt(EvaluationResult(overall_score=3.5), skill_tag="python")
    assert session.current_difficulty == QuestionDifficulty.EASY


def test_session_skill_scores():
    from app.services.interview_engine import InterviewSession
    from app.ai.answer_evaluator import EvaluationResult
    session = InterviewSession(uuid.uuid4())
    session.record_and_adapt(EvaluationResult(overall_score=8.0), skill_tag="python")
    session.record_and_adapt(EvaluationResult(overall_score=6.0), skill_tag="python")
    session.record_and_adapt(EvaluationResult(overall_score=9.0), skill_tag="sql")
    assert session.aggregated_skill_scores == {"python": 7.0, "sql": 9.0}
    assert session.consecutive_weaknesses.get("python", 0) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Integration test: start interview endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def resume_parsed():
    return {
        "Name": "Jane Doe",
        "Skills": ["Python", "FastAPI"],
        "Technologies": ["Docker"],
        "Experience": ["SWE at Tech Corp (2020-2023)"],
        "Projects": ["AI Platform"],
        "Education": ["B.S. CS"],
    }


@pytest.fixture
def job_dict():
    return {
        "title": "Backend Engineer",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["Docker"],
        "experience_years": "3+ years",
        "education_requirement": "B.S.",
        "technologies": ["PostgreSQL"],
        "seniority": "Mid-Level",
    }


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_start_interview_endpoint(async_client, mock_db_session, resume_parsed, job_dict):
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    job_id = uuid.uuid4()
    interview_id = uuid.uuid4()

    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    resume = Resume(id=resume_id, candidate_id=profile_id, file_path="f.txt",
                    file_type=FileType.TXT, parsed_data=resume_parsed)
    job = Job(id=job_id, title=job_dict["title"], description="...",
              required_skills=job_dict["required_skills"],
              preferred_skills=job_dict["preferred_skills"],
              experience_years=job_dict["experience_years"],
              education_requirement=job_dict["education_requirement"],
              technologies=job_dict["technologies"],
              seniority=job_dict["seniority"])
    profile = CandidateProfile(id=profile_id, user_id=user_id)

    # Build a mock interview with pre-generated questions
    interview = Interview(
        id=interview_id, candidate_id=profile_id, job_id=job_id,
        resume_id=resume_id, status=InterviewStatus.NOT_STARTED, total_questions=3,
    )

    q1 = InterviewQuestion(
        id=uuid.uuid4(), interview_id=interview_id,
        question_text="Explain Python decorators.", category=QuestionCategory.TECHNICAL,
        difficulty=QuestionDifficulty.MEDIUM, skill_tag="python", sequence_number=1,
    )

    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})

    # Mock DB calls in order:
    # 1. get_current_user → user
    # 2. fetch resume
    # 3. fetch job
    # 4. fetch candidate profile
    # 5. get_or_create_interview (in generate_and_save_questions) → existing interview
    # 6. start_interview: fetch interview
    # 7. _pick_next_question: select questions

    mock_user_res = MagicMock(); mock_user_res.scalar_one_or_none.return_value = user
    mock_resume_res = MagicMock(); mock_resume_res.scalar_one_or_none.return_value = resume
    mock_job_res = MagicMock(); mock_job_res.scalar_one_or_none.return_value = job
    mock_profile_res = MagicMock(); mock_profile_res.scalar_one_or_none.return_value = profile
    mock_interview_res = MagicMock(); mock_interview_res.scalar_one_or_none.return_value = interview
    mock_start_res = MagicMock(); mock_start_res.scalar_one_or_none.return_value = interview

    
    mock_messages_res = MagicMock()
    mock_messages_res.scalars.return_value.all.return_value = []

    mock_db_session.execute.side_effect = [
        mock_user_res,       # get_current_user
        mock_resume_res,     # fetch resume
        mock_job_res,        # fetch job
        mock_profile_res,    # fetch profile
        mock_interview_res,  # get_or_create_interview → existing
        mock_interview_res,  # get_interview_state: fetch interview
        mock_messages_res,   # get_interview_state: fetch messages
    ]

    # Patch dedup to avoid loading model
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        # Clear the session cache to avoid stale state
        from app.services.interview_engine import _sessions
        _sessions.clear()

        response = await async_client.post(
            "/api/v1/interviews",
            json={"resume_id": str(resume_id), "job_id": str(job_id)},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "NOT_STARTED"
    assert data["interview_id"] == str(interview_id)


@pytest.mark.skip(reason="Requires schema update")
def test_evaluate_answer_deterministic():
    """Same input should always produce the same score."""
    from app.ai.answer_evaluator import evaluate_answer
    r1 = evaluate_answer("Q?", "A", skill_tag="x")
    r2 = evaluate_answer("Q?", "A", skill_tag="x")
    assert r1.overall_score == r2.overall_score
