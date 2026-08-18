import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from app.models.interview import Interview
from app.models.question import InterviewQuestion, QuestionCategory
from app.models.answer import InterviewAnswer
from app.models.evaluation import Evaluation
from app.ai.report_generator import generate_interview_report

@pytest.mark.asyncio
async def test_generate_interview_report_no_data():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    interview_id = uuid.uuid4()
    report = await generate_interview_report(interview_id, mock_db)
    
    assert report.overall_score == 0.0
    assert report.summary == "No questions answered."
    assert "insufficient data" in report.recommendation

@pytest.mark.asyncio
async def test_generate_interview_report_with_data():
    mock_db = AsyncMock()
    
    eval1 = Evaluation(overall_score=8.0, clarity=7.5, reasoning=8.0)
    q1 = InterviewQuestion(category=QuestionCategory.TECHNICAL, skill_tag="Python")
    ans1 = InterviewAnswer()
    
    eval2 = Evaluation(overall_score=9.0, clarity=8.5, reasoning=8.5)
    q2 = InterviewQuestion(category=QuestionCategory.TECHNICAL, skill_tag="Docker")
    ans2 = InterviewAnswer()
    
    eval3 = Evaluation(overall_score=7.0, clarity=7.0, reasoning=7.0)
    q3 = InterviewQuestion(category=QuestionCategory.BEHAVIORAL, skill_tag="Leadership")
    ans3 = InterviewAnswer()
    
    records = [
        (eval1, q1, ans1),
        (eval2, q2, ans2),
        (eval3, q3, ans3),
    ]
    
    mock_result = MagicMock()
    mock_result.all.return_value = records
    mock_db.execute.return_value = mock_result
    
    # Needs MagicMock for add
    mock_db.add = MagicMock()
    
    interview_id = uuid.uuid4()
    report = await generate_interview_report(interview_id, mock_db)
    
    # The avg of (8+9+7)/3 = 8.0, scaled to 100 = 80.0
    assert report.overall_score == 80.0
    # Tech avg of (8+9)/2 = 8.5, scaled to 100 = 85.0
    assert report.technical_score == 85.0
    # Behav avg of 7, scaled to 100 = 70.0
    assert report.behavioral_score == 70.0
    # Comm avg of (7.5+8.5+7.0)/3 = 7.666 -> 76.7
    assert report.communication_score == 76.7
    # Prob avg of (8.0+8.5)/2 = 8.25 -> 82.5
    assert report.problem_solving_score == 82.5
    
    assert "Python" in report.strong_skills or "Docker" in report.strong_skills
    assert "Disclaimer: This recommendation is AI-assisted" in report.recommendation
    assert mock_db.add.called
