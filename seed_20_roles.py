import asyncio
from app.core.database import AsyncSessionLocal
from app.models.job import Job
from sqlalchemy import delete

ROLES = [
    "Software Engineer / SDE",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Mobile App Developer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Data Analyst",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "Generative AI Engineer",
    "Cybersecurity Engineer",
    "QA / Test Engineer",
    "Automation Test Engineer / SDET",
    "Database Engineer",
    "Embedded Software Engineer",
    "Systems Engineer",
    "Software Architect"
]

async def seed():
    async with AsyncSessionLocal() as db:
        # First, clear existing jobs to avoid duplicates and remove the old 'Acme Corp' job
        await db.execute(delete(Job))
        
        for role in ROLES:
            job = Job(
                title=role,
                company="Standard Interview",
                description=f"Standard interview process for {role}.",
                required_skills=["Core Concepts", "Problem Solving", "System Design"],
                experience_years="Any",
                seniority="Any",
            )
            db.add(job)
        await db.commit()
        print("20 standard roles added successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
