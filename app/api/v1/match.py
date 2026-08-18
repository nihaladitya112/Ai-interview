import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.job import Job
from app.models.match import MatchRecord
from app.schemas.match import MatchRequest, MatchResult, MatchResponse
from app.ai.matcher import match_resume_to_job

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=MatchResponse)
async def match_resume_job(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantically match a resume against a job description and save to DB.
    """
    # Fetch resume
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

    # Fetch job
    try:
        job_uuid = uuid.UUID(request.job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job_result = await db.execute(select(Job).where(Job.id == job_uuid))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Build job dict from model fields for the matcher
    job_dict = {
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "experience_years": job.experience_years or "",
        "education_requirement": job.education_requirement or "",
        "technologies": job.technologies or [],
    }

    match_result = match_resume_to_job(resume.parsed_data, job_dict)

    # Save MatchRecord
    record = MatchRecord(
        id=uuid.uuid4(),
        resume_id=resume_uuid,
        job_id=job_uuid,
        overall_score=match_result.overall_score,
        skill_score=match_result.skill_score,
        experience_score=match_result.experience_score,
        education_score=match_result.education_score,
        matched_skills=match_result.matched_skills,
        missing_skills=match_result.missing_skills,
        strengths=match_result.strengths,
        weaknesses=match_result.weaknesses,
        created_at=datetime.now(timezone.utc)
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    
    return record


@router.get("/{id}", response_model=MatchResponse)
async def get_match_record(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve an existing match record by ID.
    """
    result = await db.execute(select(MatchRecord).where(MatchRecord.id == id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Match not found")
        
    return record
