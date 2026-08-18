import asyncio
from app.ai.question_generator import generate_questions

async def main():
    qs = await generate_questions(
        resume_parsed={"Skills": ["Python", "Docker"]},
        job_dict={"title": "Software Engineer"},
        count=5
    )
    print("Generated:", qs)

if __name__ == "__main__":
    asyncio.run(main())
