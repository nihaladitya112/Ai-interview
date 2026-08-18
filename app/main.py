from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from redis import asyncio as aioredis
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager

from app.api.v1 import health, auth, users, resumes, jobs, match, questions, interview, knowledge, candidates, tasks, notifications
from app.core.config import settings
from sqlalchemy import text
from app.core.exceptions import PlatformException, platform_exception_handler
from app.core.logging import logger
from app.core.database import Base, engine
import app.models # Register all models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            logger.warning(f"Failed to create vector extension (might already exist): {e}")
        await conn.run_sync(Base.metadata.create_all)
            
    redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis)
    yield
    await redis.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(PlatformException, platform_exception_handler)  # type: ignore

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception):
        logger.error(f"Unhandled Server Error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    # Include routers
    from app.api.v1 import dashboard
    
    app.include_router(health.router, prefix=settings.API_V1_STR)
    app.include_router(auth.router, prefix=settings.API_V1_STR)
    app.include_router(users.router, prefix=settings.API_V1_STR)
    app.include_router(resumes.router, prefix=settings.API_V1_STR)
    app.include_router(jobs.router, prefix=settings.API_V1_STR)
    app.include_router(match.router, prefix=settings.API_V1_STR)
    app.include_router(questions.router, prefix=settings.API_V1_STR)
    app.include_router(interview.router, prefix=settings.API_V1_STR)
    app.include_router(knowledge.router, prefix=settings.API_V1_STR)
    app.include_router(candidates.router, prefix=settings.API_V1_STR)
    app.include_router(tasks.router, prefix=settings.API_V1_STR)
    app.include_router(dashboard.router, prefix=settings.API_V1_STR)
    app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications")
    
    # Mount frontend static files
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
