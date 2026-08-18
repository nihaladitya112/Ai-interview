import asyncio
from app.core.database import async_session_maker
from sqlalchemy import select
from app.models.interview import Interview, InterviewStatus
from app.models.candidate import CandidateProfile
from app.models.resume import Resume
from app.models.job import Job

async def main():
    async with async_session_maker() as db:
        # Try to find a NOT_STARTED interview
        query = (
            select(Interview, CandidateProfile.user_id)
            .join(Resume, Resume.id == Interview.resume_id)
            .join(CandidateProfile, CandidateProfile.id == Resume.candidate_id)
            .limit(1)
        )
        res = await db.execute(query)
        result = res.first()
        if result:
            interview, user_id = result
            print(f"Found interview: {interview.id}, User: {user_id}")
        else:
            print("No interview found")

asyncio.run(main())
