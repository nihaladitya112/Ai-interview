"""
Interview API
=============
POST /api/v1/interviews                 — Create a new interview session
POST /api/v1/interviews/{id}/start      — Start the interview session
POST /api/v1/interviews/{id}/answer     — Submit an answer to the current question
POST /api/v1/interviews/{id}/finish     — Finish the interview and generate report
GET  /api/v1/interviews/{id}            — Get full interview state
GET  /api/v1/interviews/{id}/report     — Get generated interview report
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.interview import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    InterviewStateResponse,
    SubmitAnswerResponse,
)
from app.schemas.report import InterviewReportResponse
from app.services.interview_engine import (
    start_interview,
    submit_answer,
    get_interview_state,
)
from app.services.question_service import generate_and_save_questions
from app.ai.report_generator import generate_interview_report
from app.models.resume import Resume
from app.models.job import Job
from app.models.candidate import CandidateProfile
from app.models.report import InterviewReport
from app.models.interview import Interview, InterviewStatus
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interviews", tags=["interviews"])

async def _get_interview_for_user(interview_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Interview:
    result = await db.execute(
        select(Interview)
        .join(CandidateProfile)
        .where(Interview.id == interview_id, CandidateProfile.user_id == user_id)
    )
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return interview

from fastapi_limiter.depends import RateLimiter

@router.post("", response_model=InterviewStateResponse, status_code=status.HTTP_201_CREATED)
async def create_interview_endpoint(
    request: StartInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new AI interview session.

    1. Resolves the resume and job
    2. Generates interview questions (if not already generated)
    """
    # Resolve candidate profile
    profile_result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    # Resolve resume
    resume = None
    if request.resume_id:
        try:
            resume_uuid = uuid.UUID(request.resume_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resume_id format")

        resume_result = await db.execute(select(Resume).where(Resume.id == resume_uuid))
        resume = resume_result.scalar_one_or_none()
    else:
        # Fetch the most recent resume for this candidate
        resume_result = await db.execute(
            select(Resume)
            .where(Resume.candidate_id == profile.id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        resume = resume_result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="No resume found. Please upload a resume first.")
    if not resume.parsed_data:
        raise HTTPException(status_code=422, detail="Resume has not been parsed yet")

    # Resolve job if provided
    job = None
    if request.job_id:
        try:
            job_uuid = uuid.UUID(request.job_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job_id format")

        job_result = await db.execute(select(Job).where(Job.id == job_uuid))
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    # Generate questions and get the interview
    gen_response = await generate_and_save_questions(
        resume=resume, candidate_id=profile.id, db=db, job=job, count=30,
    )
    interview_id = uuid.UUID(gen_response.interview_id)

    # Get the state
    try:
        state = await get_interview_state(interview_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return state

@router.post("/{interview_id}/start", response_model=InterviewStateResponse)
async def start_existing_interview_endpoint(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an already created interview."""
    interview = await _get_interview_for_user(interview_id, current_user.id, db)
    if interview.status != InterviewStatus.NOT_STARTED:
         raise HTTPException(status_code=400, detail="Interview already started")
    try:
        state = await start_interview(interview_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return state


@router.post("/{interview_id}/answer", response_model=SubmitAnswerResponse)
async def submit_answer_endpoint(
    interview_id: uuid.UUID,
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit an answer to the current interview question."""
    try:
        response = await submit_answer(interview_id, request.answer_text, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return response


from fastapi import UploadFile, File
from app.ai.audio_transcriber import transcribe_audio

@router.post("/{interview_id}/transcribe")
async def transcribe_answer_endpoint(
    interview_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transcribe an audio file using Whisper AI."""
    # Ensure interview exists for this user
    await _get_interview_for_user(interview_id, current_user.id, db)
    
    # Read raw audio
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")
        
    filename = file.filename or "audio.webm"
    
    try:
        text = await transcribe_audio(filename, audio_bytes)
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Failed to transcribe audio")


@router.get("/{interview_id}", response_model=InterviewStateResponse)
async def get_state_endpoint(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full interview state including conversation history and scores."""
    try:
        state = await get_interview_state(interview_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return state

@router.post("/{interview_id}/finish")
async def finish_interview_endpoint(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate final interview report and mark interview as COMPLETED."""
    interview = await _get_interview_for_user(interview_id, current_user.id, db)
    
    from app.worker import generate_interview_report_task
    task = generate_interview_report_task.delay(str(interview_id))
    
    return {
        "task_id": task.id,
        "status": "processing"
    }

@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
async def get_report(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch the generated interview report."""
    interview = await _get_interview_for_user(interview_id, current_user.id, db)
    
    query = select(InterviewReport).where(InterviewReport.interview_id == interview_id)
    result = await db.execute(query)
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet.")
        
    return report
