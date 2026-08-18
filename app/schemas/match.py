from pydantic import BaseModel
from typing import List

class MatchRequest(BaseModel):
    resume_id: str
    job_id: str

class MatchResult(BaseModel):
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]

from pydantic import ConfigDict
from datetime import datetime
import uuid

class MatchResponse(MatchResult):
    id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
