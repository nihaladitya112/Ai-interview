import asyncio
from openai import AsyncOpenAI

async def main():
    client = AsyncOpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    response = await client.chat.completions.create(
        model="llama3.1",
        messages=[
            {"role": "user", "content": "Return exactly: [{\"question_text\": \"Hi\"}]"}
        ],
        temperature=0.7
    )
    print("CONTENT:", repr(response.choices[0].message.content))

asyncio.run(main())
