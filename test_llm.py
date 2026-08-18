import asyncio
from app.ai.question_generator import generate_questions
from app.core.config import settings

async def main():
    resume_parsed = {"Experience": ["SWE at Google"]}
    job_dict = {"title": "SWE", "required_skills": ["Python"]}
    questions = await generate_questions(resume_parsed, job_dict, count=2)
    print("Got questions:", len(questions))
    for q in questions:
        print(q.question_text)

asyncio.run(main())
