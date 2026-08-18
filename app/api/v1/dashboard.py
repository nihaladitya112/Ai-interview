from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.models.candidate import CandidateProfile
from app.models.interview import Interview, InterviewStatus
from app.models.match import MatchRecord
from app.models.job import Job
from app.models.user import User
from app.models.skill import CandidateSkill, Skill
from app.deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    # 1. Total Candidates
    total_candidates_result = await db.execute(select(func.count(CandidateProfile.id)))
    total_candidates = total_candidates_result.scalar() or 0

    # 2. Active Interviews
    active_interviews_result = await db.execute(
        select(func.count(Interview.id)).where(Interview.status != InterviewStatus.COMPLETED)
    )
    active_interviews = active_interviews_result.scalar() or 0

    # 3. Avg Match Score
    avg_match_score_result = await db.execute(select(func.avg(MatchRecord.overall_score)))
    avg_match_score = avg_match_score_result.scalar() or 0
    avg_match_score = round(avg_match_score, 0)

    # 4. Recent Candidates (from matches)
    from app.models.resume import Resume
    
    recent_query = (
        select(MatchRecord, CandidateProfile, User, Job)
        .join(Resume, Resume.id == MatchRecord.resume_id)
        .join(CandidateProfile, CandidateProfile.id == Resume.candidate_id)
        .join(User, User.id == CandidateProfile.user_id)
        .join(Job, Job.id == MatchRecord.job_id)
        .order_by(desc(MatchRecord.created_at))
        .limit(5)
    )
    recent_result = await db.execute(recent_query)
    
    recent_candidates = []
    for match, profile, user, job in recent_result.all():
        # Get interview status if exists
        interview_result = await db.execute(
            select(Interview).where(
                Interview.resume_id == match.resume_id,
                Interview.job_id == match.job_id
            )
        )
        interview = interview_result.scalar_one_or_none()
        status_str = interview.status.value if interview else "SCREENING"
        
        recent_candidates.append({
            "name": f"{profile.first_name or ''} {profile.last_name or ''}".strip() or "Candidate",
            "email": user.email,
            "role": job.title,
            "match_score": round(match.overall_score, 0),
            "status": status_str,
            "initials": (user.email[0:2]).upper(),
            "interview_id": str(interview.id) if interview else None
        })
        
    # 5. Top Talent
    top_query = (
        select(MatchRecord, CandidateProfile, Job)
        .join(Resume, Resume.id == MatchRecord.resume_id)
        .join(CandidateProfile, CandidateProfile.id == Resume.candidate_id)
        .join(Job, Job.id == MatchRecord.job_id)
        .order_by(desc(MatchRecord.overall_score))
        .limit(3)
    )
    top_result = await db.execute(top_query)
    
    top_talent = []
    for match, profile, job in top_result.all():
        top_talent.append({
            "name": f"{profile.first_name or ''} {profile.last_name or ''}".strip() or "Candidate",
            "role": job.title,
            "match_score": round(match.overall_score, 0)
        })

    return {
        "total_candidates": total_candidates,
        "active_interviews": active_interviews,
        "avg_match_score": avg_match_score,
        "recent_candidates": recent_candidates,
        "top_talent": top_talent
    }

@router.get("/candidate_summary")
async def get_candidate_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get candidate profile
    profile_result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        return {
            "total_interviews": 0,
            "pending_interviews": 0,
            "avg_match_score": 0,
            "recent_candidates": [],
            "top_talent": []
        }
    
    # 1. Total Interviews
    total_interviews_result = await db.execute(
        select(func.count(Interview.id)).where(Interview.candidate_id == profile.id)
    )
    total_interviews = total_interviews_result.scalar() or 0

    # 2. Pending Interviews
    pending_interviews_result = await db.execute(
        select(func.count(Interview.id)).where(
            Interview.candidate_id == profile.id,
            Interview.status != InterviewStatus.COMPLETED
        )
    )
    pending_interviews = pending_interviews_result.scalar() or 0

    # 3. Avg Evaluation Score
    avg_score_result = await db.execute(
        select(func.avg(Interview.overall_score)).where(
            Interview.candidate_id == profile.id,
            Interview.status == InterviewStatus.COMPLETED
        )
    )
    avg_score = avg_score_result.scalar() or 0
    avg_score = round(avg_score, 0)

    # 4. Recent Interviews (using `recent_candidates` key for frontend compat)
    recent_query = (
        select(Interview, Job)
        .outerjoin(Job, Job.id == Interview.job_id)
        .where(Interview.candidate_id == profile.id)
        .order_by(desc(Interview.created_at))
        .limit(5)
    )
    recent_result = await db.execute(recent_query)
    
    recent_candidates = []
    for interview, job in recent_result.all():
        title = job.title if job else "General Interview"
        recent_candidates.append({
            "name": title,
            "email": job.company if job and job.company else "-",
            "role": interview.created_at.strftime("%b %d, %Y"),
            "match_score": round(interview.overall_score or 0, 0),
            "status": interview.status.value,
            "initials": (title[:2]).upper(),
            "interview_id": str(interview.id)
        })
        
    # 5. Top Skills (using `top_talent` key for frontend compat)
    top_skills_query = (
        select(CandidateSkill, Skill)
        .join(Skill, Skill.id == CandidateSkill.skill_id)
        .where(CandidateSkill.candidate_id == profile.id)
        .order_by(desc(CandidateSkill.proficiency_score))
        .limit(5)
    )
    top_skills_result = await db.execute(top_skills_query)
    
    top_talent = []
    for c_skill, skill in top_skills_result.all():
        score = c_skill.proficiency_score or 0
        proficiency_str = "Expert" if score > 8 else "Advanced" if score > 6 else "Intermediate" if score > 4 else "Beginner"
        top_talent.append({
            "name": skill.name,
            "role": proficiency_str,
            "match_score": round(score * 10, 0) # Scale roughly to 100
        })

    return {
        "total_interviews": total_interviews,
        "pending_interviews": pending_interviews,
        "avg_match_score": avg_score,
        "recent_candidates": recent_candidates,
        "top_talent": top_talent
    }

from fastapi import HTTPException
from app.core.security import create_access_token

@router.get("/demo-interview")
async def get_demo_interview(db: AsyncSession = Depends(get_db)):
    """Find an uncompleted interview to use for the live demo."""
    from app.models.resume import Resume
    
    # Look for any interview that is NOT_STARTED or IN_PROGRESS
    query = (
        select(Interview, CandidateProfile.user_id)
        .join(Resume, Resume.id == Interview.resume_id)
        .join(CandidateProfile, CandidateProfile.id == Resume.candidate_id)
        .where(Interview.status != InterviewStatus.COMPLETED)
        .limit(1)
    )
    res = await db.execute(query)
    result = res.first()
    
    if not result:
        raise HTTPException(status_code=404, detail="No uncompleted interviews found. Please run e2e_test.py first to seed data.")
        
    interview, user_id = result
    
    # Generate token for this user
    access_token = create_access_token(data={"sub": str(user_id)})
    
    return {
        "interview_id": str(interview.id),
        "access_token": access_token,
        "status": interview.status.value
    }

