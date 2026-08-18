from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi_limiter.depends import RateLimiter
import uuid

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.resume import Resume
from app.models.candidate import CandidateProfile
from app.services.resume_service import process_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        profile = CandidateProfile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    ALLOWED_MIME_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"]
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported media type")
        
    filename = file.filename or "unknown"
    ext = filename.split(".")[-1].upper()
    if ext not in ["PDF", "DOCX", "TXT"]:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT are supported")
        
    import os
    from app.worker import process_resume_task
    
    UPLOAD_DIR = "uploads/resumes"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")
    
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    with open(save_path, "wb") as f:
        f.write(file_bytes)
        
    # Delete previous resumes for this candidate
    from sqlalchemy import delete
    await db.execute(delete(Resume).where(Resume.candidate_id == profile.id))
    await db.commit()
        
    task = process_resume_task.delay(save_path, filename, ext, str(profile.id), str(file_id))
    return {"task_id": task.id, "status": "processing", "resume_id": str(file_id)}

@router.get("")
async def list_resumes(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all resumes for the current user, most recent first."""
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        return []
    
    result = await db.execute(
        select(Resume)
        .where(Resume.candidate_id == profile.id)
        .order_by(Resume.created_at.desc())
    )
    resumes = result.scalars().all()
    
    return [
        {
            "id": str(r.id),
            "file_name": r.file_name,
            "file_type": r.file_type.value,
            "created_at": r.created_at,
            "parsed_data": r.parsed_data,
        }
        for r in resumes
    ]

@router.get("/{id}")
async def get_resume(id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Resume).where(Resume.id == id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return {
        "id": str(resume.id),
        "file_name": resume.file_name,
        "file_type": resume.file_type.value,
        "created_at": resume.created_at
    }

@router.get("/{id}/parsed")
async def get_parsed_resume(id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Resume).where(Resume.id == id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return resume.parsed_data
