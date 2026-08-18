"""
Knowledge API
=============
POST /api/v1/knowledge/ingest
POST /api/v1/knowledge/search
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.knowledge import (
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeChunkResult,
)
from app.ai.rag_service import ingest_document, retrieve_context

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def api_ingest_document(
    request: KnowledgeIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can ingest knowledge.")
        
    from app.worker import ingest_document_task
    task = ingest_document_task.delay(request.domain, request.title, request.content, request.source_url)
    
    return {
        "task_id": task.id,
        "status": "processing"
    }


@router.post("/search", response_model=KnowledgeSearchResponse)
async def api_search_knowledge(
    request: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunks = await retrieve_context(
        db=db,
        query=request.query,
        domain=request.domain,
        limit=request.limit
    )
    
    results = [
        KnowledgeChunkResult(document_id=c.document_id, content=c.content)
        for c in chunks
    ]
    
    return KnowledgeSearchResponse(results=results)
