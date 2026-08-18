import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job
from app.schemas.job import JobCreate
from app.ai.llm_extractor import extract_job_description

async def process_job(job_in: JobCreate, db: AsyncSession) -> Job:
    parsed_data = extract_job_description(job_in.description)
    
    new_job = Job(
        id=uuid.uuid4(),
        title=parsed_data.get("Role", job_in.title),
        company=job_in.company,
        description=job_in.description,
        required_skills=parsed_data.get("Required skills", []),
        preferred_skills=parsed_data.get("Preferred skills", []),
        responsibilities=parsed_data.get("Responsibilities", []),
        seniority=parsed_data.get("Seniority"),
        experience_years=parsed_data.get("Experience"),
        education_requirement=parsed_data.get("Education"),
        technologies=parsed_data.get("Technologies", [])
    )
    
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)
    return new_job
