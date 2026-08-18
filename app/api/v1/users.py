from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.deps import get_current_user, require_role
from app.models.user import User
from app.core.database import get_db
from app.core import security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

router = APIRouter(prefix="/users", tags=["users"])

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str

@router.get("/me", summary="Return the authenticated user's profile")
async def read_me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.candidate import CandidateProfile
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "first_name": profile.first_name if profile else None,
        "last_name": profile.last_name if profile else None,
        "phone": profile.phone if profile else None
    }

@router.put("/me", summary="Update the authenticated user's profile details")
async def update_me(update_data: UserUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.candidate import CandidateProfile
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)
    
    if update_data.first_name is not None:
        profile.first_name = update_data.first_name
    if update_data.last_name is not None:
        profile.last_name = update_data.last_name
    if update_data.phone is not None:
        profile.phone = update_data.phone
        
    await db.commit()
    return {"message": "Profile updated successfully"}

@router.put("/me/password", summary="Update the authenticated user's password")
async def update_password(update_data: PasswordUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not security.verify_password(update_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
        
    current_user.hashed_password = security.get_password_hash(update_data.new_password)
    await db.commit()
    return {"message": "Password updated successfully"}

@router.get("/me/stats", summary="Return the authenticated user's statistics")
async def read_me_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.candidate import CandidateProfile
    from app.models.interview import Interview, InterviewStatus
    
    # Get profile
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        return {"total_interviews": 0, "completed_interviews": 0, "avg_score": 0}
        
    # Get total interviews
    total_interviews_res = await db.execute(select(func.count(Interview.id)).where(Interview.candidate_id == profile.id))
    total_interviews = total_interviews_res.scalar() or 0
    
    # Get completed interviews
    completed_interviews_res = await db.execute(
        select(func.count(Interview.id))
        .where(Interview.candidate_id == profile.id)
        .where(Interview.status == InterviewStatus.COMPLETED)
    )
    completed_interviews = completed_interviews_res.scalar() or 0
    
    # Get average score
    avg_score_res = await db.execute(
        select(func.avg(Interview.overall_score))
        .where(Interview.candidate_id == profile.id)
        .where(Interview.status == InterviewStatus.COMPLETED)
    )
    avg_score = avg_score_res.scalar() or 0
    
    return {
        "total_interviews": total_interviews,
        "completed_interviews": completed_interviews,
        "avg_score": round(avg_score, 0)
    }

@router.get("/me/interviews", summary="Return the authenticated user's past interviews")
async def read_me_interviews(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.candidate import CandidateProfile
    from app.models.interview import Interview
    from app.models.job import Job
    
    # Get profile
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        return []
        
    # Get interviews with jobs (using outerjoin in case job is missing)
    query = (
        select(Interview, Job)
        .outerjoin(Job, Job.id == Interview.job_id)
        .where(Interview.candidate_id == profile.id)
        .order_by(desc(Interview.created_at))
    )
    result = await db.execute(query)
    
    interviews = []
    for interview, job in result.all():
        interviews.append({
            "id": str(interview.id),
            "job_title": job.title if job else "General Interview",
            "company": job.company if job and job.company else "InterviewAI",
            "status": interview.status.value,
            "created_at": interview.created_at,
            "completed_at": interview.completed_at
        })
        
    return interviews

@router.get("", summary="List all users (Admin only)")
async def read_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "email": u.email, "role": u.role.value} for u in users]
