"""
Question Service
================
Orchestrates interview creation and bulk-inserts generated questions.
"""
from __future__ import annotations

import uuid
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.interview import Interview, InterviewStatus
from app.models.question import InterviewQuestion, QuestionCategory, QuestionDifficulty
from app.models.resume import Resume
from app.models.job import Job
from app.ai.question_generator import generate_questions
from app.schemas.questions import GeneratedQuestion, QuestionGenerationResponse

logger = logging.getLogger(__name__)


async def get_or_create_interview(
    candidate_id: uuid.UUID,
    resume_id: uuid.UUID,
    db: AsyncSession,
    job_id: Optional[uuid.UUID] = None,
) -> Interview:
    """Delete any existing NOT_STARTED interview and create a fresh one."""
    query = select(Interview).where(
        Interview.candidate_id == candidate_id,
        Interview.status == InterviewStatus.NOT_STARTED,
    )
    result = await db.execute(query)
    old_interviews = result.scalars().all()
    for old_int in old_interviews:
        await db.delete(old_int)
    await db.flush()

    interview = Interview(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        resume_id=resume_id,
        status=InterviewStatus.NOT_STARTED,
    )
    db.add(interview)
    await db.flush()   # get the ID without full commit
    return interview


async def generate_and_save_questions(
    resume: Resume,
    candidate_id: uuid.UUID,
    db: AsyncSession,
    job: Optional[Job] = None,
    count: int = 15,
    categories: Optional[List[QuestionCategory]] = None,
    difficulties: Optional[List[QuestionDifficulty]] = None,
) -> QuestionGenerationResponse:
    """Full pipeline: build context → generate → deduplicate → persist."""
    if not resume.parsed_data:
        raise ValueError("Resume has not been parsed yet")

    if job:
        job_dict = {
            "title": job.title,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "experience_years": job.experience_years or "",
            "education_requirement": job.education_requirement or "",
            "technologies": job.technologies or [],
            "seniority": job.seniority or "Mid-Level",
        }
    else:
        # Fallback to an empty dictionary or a placeholder dictionary if no job is provided.
        job_dict = {
            "title": "General Role based on Resume",
            "required_skills": resume.parsed_data.get("Skills", []),
            "preferred_skills": resume.parsed_data.get("Technologies", []),
            "experience_years": "Any",
            "education_requirement": "Any",
            "technologies": resume.parsed_data.get("Technologies", []),
            "seniority": "Any",
        }

    # 1. Fetch previously generated questions for this candidate
    past_interviews_query = select(Interview.id).where(Interview.candidate_id == candidate_id)
    past_interviews_result = await db.execute(past_interviews_query)
    past_interview_ids = [row[0] for row in past_interviews_result.all()]
    
    past_questions = []
    if past_interview_ids:
        past_q_query = select(InterviewQuestion.question_text).where(InterviewQuestion.interview_id.in_(past_interview_ids))
        past_q_result = await db.execute(past_q_query)
        past_questions = [row[0] for row in past_q_result.all()]

    generated: List[GeneratedQuestion] = await generate_questions(
        resume_parsed=resume.parsed_data,
        job_dict=job_dict,
        count=count,
        categories=categories,
        difficulties=difficulties,
        previous_questions=past_questions,
    )

    assert resume.id is not None
    interview = await get_or_create_interview(candidate_id, resume.id, db, job.id if job else None)

    db_questions: List[InterviewQuestion] = []
    for seq, q in enumerate(generated, start=1):
        db_q = InterviewQuestion(
            id=uuid.uuid4(),
            interview_id=interview.id,
            question_text=q.question_text,
            category=q.category,
            difficulty=q.difficulty,
            skill_tag=q.skill_tag,
            sequence_number=seq,
            is_follow_up=q.is_follow_up,
        )
        db.add(db_q)
        db_questions.append(db_q)

    interview.total_questions = len(db_questions)
    await db.commit()
    await db.refresh(interview)

    return QuestionGenerationResponse(
        interview_id=str(interview.id),
        total_generated=len(generated),
        questions=generated,
    )
