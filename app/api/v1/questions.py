"""
Questions API
=============
POST /api/v1/questions/generate  — generate personalised interview questions
GET  /api/v1/questions/interview/{interview_id} — list questions for an interview
"""
from __future__ import annotations

import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.question import InterviewQuestion
from app.schemas.questions import (
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    GeneratedQuestion,
)
from app.services.question_service import generate_and_save_questions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/questions", tags=["questions"])


@router.post("/generate", response_model=QuestionGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_interview_questions(
    request: QuestionGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate personalised, de-duplicated interview questions for a resume/job pair.

    The generation engine:
    - Extracts candidate skills, projects, companies, and experience from the parsed resume
    - Fills rich template banks with those specific details
    - Applies semantic deduplication to avoid near-identical questions
    - Distributes difficulty levels per the requested profile
    - Persists the questions to an Interview record and returns the full set
    """
    # Resolve resume
    try:
        resume_uuid = uuid.UUID(request.resume_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid resume_id format")

    resume_result = await db.execute(select(Resume).where(Resume.id == resume_uuid))
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.parsed_data:
        raise HTTPException(status_code=422, detail="Resume has not been parsed yet")

    # Resolve job
    try:
        job_uuid = uuid.UUID(request.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job_result = await db.execute(select(Job).where(Job.id == job_uuid))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Resolve candidate profile for the current user
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    try:
        response = await generate_and_save_questions(
            resume=resume,
            job=job,
            candidate_id=profile.id,
            db=db,
            count=request.count,
            categories=request.categories,
            difficulties=request.difficulties,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return response


@router.get("/interview/{interview_id}", response_model=List[GeneratedQuestion])
async def get_interview_questions(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all questions for a given interview, ordered by sequence number.
    """
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.interview_id == interview_id)
        .order_by(InterviewQuestion.sequence_number)
    )
    questions = result.scalars().all()
    if not questions:
        raise HTTPException(status_code=404, detail="No questions found for this interview")

    return [
        GeneratedQuestion(
            question_text=q.question_text,
            category=q.category,
            difficulty=q.difficulty,
            skill_tag=q.skill_tag,
            is_follow_up=q.is_follow_up,
        )
        for q in questions
    ]
