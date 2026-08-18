import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.models.job import Job

async def seed():
    async with async_session_maker() as db:
        # Check if job exists
        job = Job(
            title="Senior Software Engineer",
            company="Acme Corp",
            description="We are looking for an experienced software engineer to build scalable backend systems.",
            required_skills=["Python", "FastAPI", "SQLAlchemy", "System Design"],
            experience_years="5+ years",
            seniority="Senior",
        )
        db.add(job)
        await db.commit()
        print("Job added successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
