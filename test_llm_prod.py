import asyncio
from app.ai.question_generator import generate_questions

async def main():
    resume_parsed = {"Experience": ["SWE at Google"]}
    job_dict = {"title": "SWE", "required_skills": ["Python", "AWS", "Docker"]}
    print("Starting generation...")
    questions = await generate_questions(resume_parsed, job_dict, count=15)
    print("Generated questions:", len(questions))

asyncio.run(main())
