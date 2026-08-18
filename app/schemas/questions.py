from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.question import QuestionCategory, QuestionDifficulty


class QuestionGenerationRequest(BaseModel):
    resume_id: str
    job_id: str
    count: int = Field(default=15, ge=5, le=50)
    categories: Optional[List[QuestionCategory]] = None
    difficulties: Optional[List[QuestionDifficulty]] = None


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_text: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    skill_tag: Optional[str] = None
    is_follow_up: bool = False


class QuestionGenerationResponse(BaseModel):
    interview_id: str
    total_generated: int
    questions: List[GeneratedQuestion]

