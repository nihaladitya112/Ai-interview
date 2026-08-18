import asyncio
from app.ai.llm_extractor import extract_candidate_profile
from app.ai.text_extraction import extract_text

async def main():
    text = "Nihal Aditya Attaluri\nSkills: Java, Python, React\nProjects: EventConnect"
    res = await extract_candidate_profile(text)
    print("LLM Parse:", res)

asyncio.run(main())
