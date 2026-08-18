import hashlib
import random
import uuid
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.knowledge import KnowledgeDocument, KnowledgeChunk

logger = logging.getLogger(__name__)

def _generate_mock_embedding(text: str) -> List[float]:
    """
    Generate a deterministic 1536-dimensional embedding for testing purposes.
    Simulates `text-embedding-3-small`.
    """
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    r = random.Random(seed)
    
    vector = [r.gauss(0, 1) for _ in range(1536)]
    norm = sum(x*x for x in vector) ** 0.5
    if norm == 0:
        return vector
    return [x/norm for x in vector]

def _chunk_text(text: str, max_words: int = 150) -> List[str]:
    """
    Split text into simple word-based chunks.
    In production, use semantic chunking or libraries like LangChain RecursiveCharacterTextSplitter.
    """
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks

async def ingest_document(
    db: AsyncSession,
    domain: str,
    title: str,
    content: str,
    source_url: str | None = None
) -> tuple[uuid.UUID, int]:
    """
    Ingest a new document, chunk it, embed chunks, and store in pgvector.
    """
    doc_id = uuid.uuid4()
    doc = KnowledgeDocument(
        id=doc_id,
        domain=domain,
        title=title,
        source_url=source_url
    )
    db.add(doc)
    
    chunks = _chunk_text(content)
    for text_chunk in chunks:
        embedding = _generate_mock_embedding(text_chunk)
        chunk_obj = KnowledgeChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            content=text_chunk,
            embedding=embedding
        )
        db.add(chunk_obj)
        
    await db.flush()
    return doc_id, len(chunks)

async def retrieve_context(
    db: AsyncSession,
    query: str,
    domain: str | None = None,
    limit: int = 3
) -> List[KnowledgeChunk]:
    """
    Retrieve top-K relevant chunks using HNSW cosine distance search in pgvector.
    """
    query_embedding = _generate_mock_embedding(query)
    
    stmt = select(KnowledgeChunk)
    if domain:
        stmt = stmt.join(KnowledgeDocument).where(KnowledgeDocument.domain == domain)
        
    # Use cosine distance for semantic search
    stmt = stmt.order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding)).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())
