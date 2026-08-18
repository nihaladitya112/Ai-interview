from typing import List, Optional
from pydantic import BaseModel
import uuid

class KnowledgeIngestRequest(BaseModel):
    domain: str
    title: str
    content: str
    source_url: Optional[str] = None

class KnowledgeIngestResponse(BaseModel):
    document_id: uuid.UUID
    chunks_created: int

class KnowledgeSearchRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    limit: int = 3

class KnowledgeChunkResult(BaseModel):
    document_id: uuid.UUID
    content: str

class KnowledgeSearchResponse(BaseModel):
    results: List[KnowledgeChunkResult]
