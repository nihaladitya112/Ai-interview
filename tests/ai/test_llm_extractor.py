import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai.llm_extractor import extract_candidate_profile, extract_job_description
from app.services.job_service import process_job
from app.schemas.job import JobCreate

@pytest.mark.skip(reason="Requires schema update")
def test_extract_candidate_profile():
    result = extract_candidate_profile("dummy text")
    assert "Name" in result
    assert "Skills" in result
    assert result["Name"] == "Jane Doe"

@pytest.mark.skip(reason="Requires schema update")
def test_extract_job_description():
    result = extract_job_description("dummy text")
    assert "Role" in result
    assert "Required skills" in result
    assert result["Role"] == "Backend Developer"

@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires schema update")
async def test_process_job():
    db = AsyncMock()
    job_in = JobCreate(
        title="Software Engineer",
        company="Tech Corp",
        description="Looking for a Python dev"
    )
    
    new_job = await process_job(job_in, db)
    
    # Check that parsed data overwrites some fields based on llm_extractor mock
    assert new_job.title == "Backend Developer"
    assert new_job.company == "Tech Corp"
    assert "Python" in new_job.required_skills
    assert db.add.called
    assert db.commit.called
