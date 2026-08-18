import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RecommendationCreate(BaseModel):
    interview_id: uuid.UUID

class RecommendationResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    missing_skills: Optional[List[str]] = []
    learning_topics: Optional[List[str]] = []
    prerequisites: Optional[List[str]] = []
    practice_problems: Optional[List[str]] = []
    project_recommendations: Optional[List[str]] = []
    learning_sequence: Optional[List[str]] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
