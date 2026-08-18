import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class InterviewReportResponse(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    overall_score: float
    technical_score: float
    behavioral_score: float
    problem_solving_score: float
    communication_score: float
    summary: str
    strong_skills: List[str]
    weak_skills: List[str]
    technical_gaps: List[str]
    best_answers: List[str]
    weak_answers: List[str]
    recommended_topics: List[str]
    recommendation: str

    model_config = ConfigDict(from_attributes=True)
