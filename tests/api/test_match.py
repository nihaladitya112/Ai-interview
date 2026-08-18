"""
Integration tests for POST /api/v1/match

The sentence-transformer model is mocked via monkeypatching `app.ai.matcher.embed`
so the heavy model is never loaded during the test run.
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid
import numpy as np

from app.models.user import User, UserRole
from app.models.resume import Resume, FileType
from app.models.job import Job
from app.core import security


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_resume_parsed():
    return {
        "Name": "Jane Doe",
        "Skills": ["Python", "FastAPI", "PostgreSQL", "Machine Learning"],
        "Technologies": ["Docker", "Git", "Kubernetes"],
        "Experience": ["Software Engineer at Tech Corp (2020-2023)"],
        "Education": ["B.S. Computer Science, University of Technology"],
    }


@pytest.fixture
def sample_job_dict():
    return {
        "required_skills": ["Python", "FastAPI", "SQLAlchemy"],
        "preferred_skills": ["Redis", "Docker"],
        "experience_years": "3+ years",
        "education_requirement": "Bachelor's degree in Computer Science",
        "technologies": ["Python 3.12", "PostgreSQL", "Git"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — matcher functions (no DB, no model)
# ─────────────────────────────────────────────────────────────────────────────

def make_fixed_embed(n_texts):
    """Return deterministic embeddings so similarity is predictable."""
    rng = np.random.default_rng(seed=0)
    def _embed(texts):
        vecs = rng.random((len(texts), 384)).astype(np.float32)
        # L2-normalise so cosine_similarity works correctly
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms
    return _embed


@patch("app.ai.matcher.embed", side_effect=make_fixed_embed(10))
def test_match_resume_to_job_returns_valid_structure(mock_embed, sample_resume_parsed, sample_job_dict):
    from app.ai.matcher import match_resume_to_job
    result = match_resume_to_job(sample_resume_parsed, sample_job_dict)

    assert 0 <= result.overall_score <= 100
    assert 0 <= result.skill_score <= 100
    assert 0 <= result.experience_score <= 100
    assert 0 <= result.education_score <= 100
    assert isinstance(result.matched_skills, list)
    assert isinstance(result.missing_skills, list)
    assert isinstance(result.strengths, list)
    assert isinstance(result.weaknesses, list)
    # All required skills must appear in exactly one of matched or missing
    all_skills = set(result.matched_skills) | set(result.missing_skills)
    assert all_skills == set(sample_job_dict["required_skills"])


def test_experience_score_above_requirement():
    from app.ai.matcher import score_experience
    # 3 years of experience vs 2+ required → should score 100
    score = score_experience(["Software Engineer at Corp (2020-2023)"], "2+ years")
    assert score == 100.0


def test_experience_score_below_requirement():
    from app.ai.matcher import score_experience
    # 1 year vs 5+ required → should score ~20
    score = score_experience(["Junior Dev (2023-2024)"], "5+ years")
    assert score < 30.0


@patch("app.ai.matcher.embed", side_effect=make_fixed_embed(2))
def test_education_score_returns_valid_range(mock_embed):
    from app.ai.matcher import score_education
    score = score_education(
        ["B.S. Computer Science"],
        "Bachelor's degree in Computer Science or related field"
    )
    assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Integration test — POST /api/v1/match
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("app.ai.matcher.embed", side_effect=make_fixed_embed(10))
async def test_match_endpoint(mock_embed, async_client, mock_db_session, sample_resume_parsed):
    user_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    job_id = uuid.uuid4()

    user = User(id=user_id, email="test@example.com", role=UserRole.CANDIDATE, is_active=True)
    resume = Resume(
        id=resume_id,
        candidate_id=user_id,
        file_path="uploads/resume.txt",
        file_type=FileType.TXT,
        parsed_data=sample_resume_parsed,
    )
    job = Job(
        id=job_id,
        title="Backend Developer",
        description="...",
        required_skills=["Python", "FastAPI", "SQLAlchemy"],
        preferred_skills=["Redis", "Docker"],
        experience_years="3+ years",
        education_requirement="Bachelor's degree in Computer Science",
        technologies=["PostgreSQL"],
    )

    access_token = security.create_access_token({"sub": str(user_id), "role": "CANDIDATE"})

    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user
    mock_resume_result = MagicMock()
    mock_resume_result.scalar_one_or_none.return_value = resume
    mock_job_result = MagicMock()
    mock_job_result.scalar_one_or_none.return_value = job

    mock_db_session.execute.side_effect = [mock_user_result, mock_resume_result, mock_job_result]

    response = await async_client.post(
        "/api/v1/matches",
        json={"resume_id": str(resume_id), "job_id": str(job_id)},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "skill_score" in data
    assert "experience_score" in data
    assert "matched_skills" in data
    assert "missing_skills" in data
    assert "strengths" in data
    assert "weaknesses" in data
    assert 0 <= data["overall_score"] <= 100
