import asyncio
from openai import AsyncOpenAI
import json

async def main():
    client = AsyncOpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    response = await client.chat.completions.create(
        model="llama3.1",
        messages=[
            {"role": "system", "content": "You are an expert. Return exactly 2 unique questions in a strict JSON array where each object has keys: question_text, category, difficulty, skill_tag."},
            {"role": "user", "content": "Generate the interview questions in JSON format."}
        ],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    content = response.choices[0].message.content.strip()
    print("RAW CONTENT:", content)
    
asyncio.run(main())
