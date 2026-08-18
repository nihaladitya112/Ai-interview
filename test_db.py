import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URI)

async def main():
    async with AsyncSession(engine) as db:
        res = await db.execute(text("SELECT id, status FROM interviews"))
        print("Interviews:", res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
