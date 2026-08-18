import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException
from sqlalchemy import select

from app.models.resume import Resume, FileType
from app.models.candidate import CandidateProfile
from app.ai.text_extraction import extract_text
from app.ai.llm_extractor import extract_candidate_profile

UPLOAD_DIR = "uploads/resumes"

async def process_resume_from_disk(file_path: str, filename: str, file_type: FileType, candidate_id: uuid.UUID, db: AsyncSession, file_id: uuid.UUID = None) -> Resume:
    if not file_id:
        file_id = uuid.uuid4()
        
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    raw_text = extract_text(file_bytes, file_type.value)
    parsed_data = await extract_candidate_profile(raw_text)
    
    new_resume = Resume(
        id=file_id,
        candidate_id=candidate_id,
        file_path=file_path,
        file_name=filename,
        file_type=file_type,
        raw_text=raw_text,
        parsed_data=parsed_data
    )
    db.add(new_resume)
    
    result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    profile = result.scalar_one_or_none()
    
    if profile:
        name_parts = parsed_data.get("Name", "").split(" ", 1)
        if len(name_parts) > 0 and not profile.first_name:
            profile.first_name = name_parts[0]
        if len(name_parts) > 1 and not profile.last_name:
            profile.last_name = name_parts[1]
            
        if parsed_data.get("Education"):
            profile.education_summary = str(parsed_data["Education"])
        if parsed_data.get("Experience"):
            profile.experience_summary = str(parsed_data["Experience"])
            
    await db.commit()
    await db.refresh(new_resume)
    return new_resume

async def process_resume(file: UploadFile, candidate_id: uuid.UUID, db: AsyncSession) -> Resume:
    filename = file.filename or "unknown"
    ext = filename.split(".")[-1].upper()
    if ext not in ["PDF", "DOCX", "TXT"]:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT are supported")
    
    file_type = FileType[ext]
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = uuid.uuid4()
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{filename}")
    
    file_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(file_bytes)
        
    return await process_resume_from_disk(save_path, filename, file_type, candidate_id, db, file_id)
