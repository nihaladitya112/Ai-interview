import asyncio
import uuid
import logging
from celery import Celery

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.resume import FileType
from app.services.resume_service import process_resume_from_disk
from app.ai.rag_service import ingest_document
from app.ai.report_generator import generate_interview_report
from app.models.interview import Interview, InterviewStatus
from app.models.candidate import CandidateProfile
from sqlalchemy import select
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

celery_app = Celery(
    "ai_interviewer",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)
celery_app.conf.task_track_started = True

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

def run_async(coro):
    """Run an async coroutine synchronously inside the celery worker."""
    return asyncio.run(coro)

async def _get_scoped_db():
    engine = create_async_engine(str(settings.DATABASE_URI), poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_maker()

@celery_app.task
def process_resume_task(file_path: str, filename: str, file_type_str: str, candidate_id_str: str, file_id_str: str):
    async def _do():
        engine, db = await _get_scoped_db()
        try:
            async with db:
                file_type = FileType(file_type_str)
                candidate_id = uuid.UUID(candidate_id_str)
                file_id = uuid.UUID(file_id_str)
                resume = await process_resume_from_disk(file_path, filename, file_type, candidate_id, db, file_id)
                
                # Create notification
                result = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
                candidate = result.scalars().first()
                if candidate:
                    await NotificationService.create_notification(
                        db=db,
                        user_id=candidate.user_id,
                        message="Your resume has been successfully parsed and your profile is updated.",
                        type="SUCCESS"
                    )
                
                await db.commit()
                return {"resume_id": str(resume.id)}
        finally:
            await engine.dispose()
    return run_async(_do())

@celery_app.task
def ingest_document_task(domain: str, title: str, content: str, source_url: str = None):
    async def _do():
        engine, db = await _get_scoped_db()
        try:
            async with db:
                doc_id, chunks = await ingest_document(db, domain, title, content, source_url)
                await db.commit()
                return {"document_id": str(doc_id), "chunks_created": chunks}
        finally:
            await engine.dispose()
    return run_async(_do())

@celery_app.task
def generate_interview_report_task(interview_id_str: str):
    async def _do():
        engine, db = await _get_scoped_db()
        try:
            async with db:
                interview_id = uuid.UUID(interview_id_str)
                result = await db.execute(select(Interview).where(Interview.id == interview_id))
                interview = result.scalar_one_or_none()
                if interview:
                    interview.status = InterviewStatus.COMPLETED
                
                report = await generate_interview_report(interview_id, db)
                
                # Notification
                if interview:
                    cand_res = await db.execute(select(CandidateProfile).where(CandidateProfile.id == interview.candidate_id))
                    candidate = cand_res.scalars().first()
                    if candidate:
                        await NotificationService.create_notification(
                            db=db,
                            user_id=candidate.user_id,
                            message=f"Your interview report is ready! You scored {report.overall_score}/100.",
                            type="SUCCESS"
                        )
                
                await db.commit()
                return {"report_id": str(report.id), "overall_score": report.overall_score}
        finally:
            await engine.dispose()
    return run_async(_do())
