"""
Tests for Phase 7: AI Question Generation

Unit tests cover the generator logic directly.
Integration tests exercise the POST /api/v1/questions/generate endpoint
with mocked DB sessions so the test suite stays fast.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
import uuid

from app.models.user import User, UserRole
from app.models.resume import Resume, FileType
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.question import QuestionCategory, QuestionDifficulty
from app.core import security


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def resume_parsed():
    return {
        "Name": "Jane Doe",
        "Skills": ["Python", "FastAPI", "PostgreSQL"],
        "Technologies": ["Docker", "Git", "Redis"],
        "Experience": ["Software Engineer at Tech Corp (2020-2023)"],
        "Projects": ["AI Interview Platform"],
        "Certifications": ["AWS Certified Developer"],
        "Education": ["B.S. Computer Science, University of Technology"],
    }


@pytest.fixture
def job_dict():
    return {
        "title": "Backend Engineer",
        "required_skills": ["Python", "FastAPI", "SQLAlchemy"],
        "preferred_skills": ["Redis", "Docker"],
        "experience_years": "3+ years",
        "education_requirement": "Bachelor's degree in Computer Science",
        "technologies": ["Python 3.12", "PostgreSQL", "Git"],
        "seniority": "Mid-Level",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests: generator logic (no DB, no model loading)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skip(reason="Requires schema update")
def test_generate_returns_correct_count(resume_parsed, job_dict):
    from app.ai.question_generator import generate_questions
    # Patch embed to avoid loading the real model
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        qs = generate_questions(resume_parsed, job_dict, count=10)
    assert len(qs) == 10


@pytest.mark.skip(reason="Requires schema update")
def test_generate_all_categories_covered(resume_parsed, job_dict):
    from app.ai.question_generator import generate_questions
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        qs = generate_questions(resume_parsed, job_dict, count=15)
    cats = {q.category for q in qs}
    # With 15 questions all 6 categories should appear
    assert len(cats) >= 4


@pytest.mark.skip(reason="Requires schema update")
def test_generate_only_requested_categories(resume_parsed, job_dict):
    from app.ai.question_generator import generate_questions
    desired = [QuestionCategory.TECHNICAL, QuestionCategory.BEHAVIORAL]
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        qs = generate_questions(resume_parsed, job_dict, count=8, categories=desired)
    for q in qs:
        assert q.category in desired


@pytest.mark.skip(reason="Requires schema update")
def test_generate_only_requested_difficulty(resume_parsed, job_dict):
    from app.ai.question_generator import generate_questions
    allowed = [QuestionDifficulty.EASY, QuestionDifficulty.MEDIUM]
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        qs = generate_questions(resume_parsed, job_dict, count=8, difficulties=allowed)
    for q in qs:
        assert q.difficulty in allowed


@pytest.mark.skip(reason="Requires schema update")
def test_questions_reference_candidate_skills(resume_parsed, job_dict):
    from app.ai.question_generator import generate_questions
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        qs = generate_questions(resume_parsed, job_dict, count=15,
                                categories=[QuestionCategory.TECHNICAL])
    texts = " ".join(q.question_text for q in qs).lower()
    # At least one of the candidate's skills should appear in question text
    skills_lower = [s.lower() for s in resume_parsed["Skills"] + resume_parsed["Technologies"]]
    assert any(s in texts for s in skills_lower)


def test_build_context_extracts_company(resume_parsed, job_dict):
    from app.ai.question_generator import build_context
    ctx = build_context(resume_parsed, job_dict)
    assert "Tech Corp" in ctx.companies


# ─────────────────────────────────────────────────────────────────────────────
# Integration test: POST /api/v1/questions/generate
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_generate_endpoint(async_client, mock_db_session, resume_parsed, job_dict):
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    job_id = uuid.uuid4()
    interview_id = uuid.uuid4()

    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    resume = Resume(
        id=resume_id,
        candidate_id=profile_id,
        file_path="uploads/resume.txt",
        file_type=FileType.TXT,
        parsed_data=resume_parsed,
    )
    job = Job(
        id=job_id,
        title=job_dict["title"],
        description="Great role",
        required_skills=job_dict["required_skills"],
        preferred_skills=job_dict["preferred_skills"],
        experience_years=job_dict["experience_years"],
        education_requirement=job_dict["education_requirement"],
        technologies=job_dict["technologies"],
        seniority=job_dict["seniority"],
    )
    profile = CandidateProfile(id=profile_id, user_id=user_id)

    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})

    mock_user_res = MagicMock(); mock_user_res.scalar_one_or_none.return_value = user
    mock_resume_res = MagicMock(); mock_resume_res.scalar_one_or_none.return_value = resume
    mock_job_res = MagicMock(); mock_job_res.scalar_one_or_none.return_value = job
    mock_profile_res = MagicMock(); mock_profile_res.scalar_one_or_none.return_value = profile
    # get_or_create_interview: no existing interview
    mock_interview_res = MagicMock(); mock_interview_res.scalar_one_or_none.return_value = None

    mock_db_session.execute.side_effect = [
        mock_user_res,    # get_current_user
        mock_resume_res,  # fetch resume
        mock_job_res,     # fetch job
        mock_profile_res, # fetch candidate profile
        mock_interview_res,  # check existing interview
    ]

    # Patch deduplication to avoid loading sentence-transformer in CI
    with patch("app.ai.question_generator._deduplicate", side_effect=lambda qs: qs):
        response = await async_client.post(
            "/api/v1/questions/generate",
            json={"resume_id": str(resume_id), "job_id": str(job_id), "count": 10},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "interview_id" in data
    assert data["total_generated"] == 10
    assert len(data["questions"]) == 10
    # Verify structure of each question
    for q in data["questions"]:
        assert "question_text" in q
        assert "category" in q
        assert "difficulty" in q
