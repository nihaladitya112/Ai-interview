"""
Interview Schemas
=================
Pydantic models for the interview engine API.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.interview import InterviewStatus
from app.models.question import QuestionCategory, QuestionDifficulty


class StartInterviewRequest(BaseModel):
    resume_id: Optional[str] = None
    job_id: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    answer_text: str


class AnswerEvaluationResponse(BaseModel):
    technical_correctness: float
    relevance: float
    depth: float
    reasoning: float
    clarity: float
    completeness: float
    overall_score: float
    feedback: str
    missing_concepts: List[str]
    strengths: List[str]
    weaknesses: List[str]


class CurrentQuestionInfo(BaseModel):
    question_id: str
    question_text: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    skill_tag: Optional[str] = None
    sequence_number: int


class InterviewStateResponse(BaseModel):
    interview_id: str
    status: InterviewStatus
    current_question: Optional[CurrentQuestionInfo] = None
    current_difficulty: Optional[str] = None
    questions_asked: int
    total_questions: int
    skill_scores: Dict[str, float]
    overall_score: Optional[float] = None
    conversation_history: List[Dict[str, str]]


class SubmitAnswerResponse(BaseModel):
    evaluation: AnswerEvaluationResponse
    next_question: Optional[CurrentQuestionInfo] = None
    interview_status: InterviewStatus
    message: str
