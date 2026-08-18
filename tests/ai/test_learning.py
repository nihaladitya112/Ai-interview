import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

from app.ai.learning_engine import generate_learning_path
from app.models.report import InterviewReport

@pytest.mark.asyncio
async def test_generate_learning_path_with_gaps():
    db = AsyncMock()
    mock_result = MagicMock()
    report = InterviewReport(
        interview_id=uuid.uuid4(),
        technical_gaps=["Concurrency"],
        weak_skills=["Python"]
    )
    mock_result.scalar_one_or_none.return_value = report
    db.execute.return_value = mock_result
    
    rec = await generate_learning_path(uuid.uuid4(), report.interview_id, db)
    
    assert "Concurrency" in rec.missing_skills or "Python" in rec.missing_skills
    assert db.add.called
    assert db.commit.called

@pytest.mark.asyncio
async def test_generate_learning_path_no_gaps():
    db = AsyncMock()
    mock_result = MagicMock()
    report = InterviewReport(
        interview_id=uuid.uuid4(),
        technical_gaps=[],
        weak_skills=[]
    )
    mock_result.scalar_one_or_none.return_value = report
    db.execute.return_value = mock_result
    
    rec = await generate_learning_path(uuid.uuid4(), report.interview_id, db)
    
    assert "Advanced System Design" in rec.missing_skills
    assert db.add.called
    
@pytest.mark.asyncio
async def test_generate_learning_path_no_report():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    
    with pytest.raises(ValueError):
        await generate_learning_path(uuid.uuid4(), uuid.uuid4(), db)
