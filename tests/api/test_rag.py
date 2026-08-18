import pytest
from unittest.mock import AsyncMock, MagicMock
import uuid

from app.ai.rag_service import ingest_document, retrieve_context, _generate_mock_embedding
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk

@pytest.mark.asyncio
async def test_generate_mock_embedding():
    emb1 = _generate_mock_embedding("Python is great")
    emb2 = _generate_mock_embedding("Python is great")
    emb3 = _generate_mock_embedding("Java is okay")
    
    assert len(emb1) == 1536
    assert emb1 == emb2
    assert emb1 != emb3

@pytest.mark.asyncio
async def test_ingest_document():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    content = "This is a test document. " * 300  # Will be chunked
    
    doc_id, num_chunks = await ingest_document(
        db=mock_db,
        domain="Python",
        title="Python Guide",
        content=content
    )
    
    assert doc_id is not None
    assert num_chunks > 1
    assert mock_db.add.called
    assert mock_db.flush.called

@pytest.mark.asyncio
async def test_retrieve_context():
    mock_db = AsyncMock()
    
    # Mock the SQLAlchemy execute result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    
    chunk = KnowledgeChunk(
        id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        content="Python uses indentation",
        embedding=[0.0]*1536
    )
    
    mock_scalars.all.return_value = [chunk]
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result
    
    chunks = await retrieve_context(mock_db, "What does Python use for blocks?", "Python")
    
    assert len(chunks) == 1
    assert chunks[0].content == "Python uses indentation"
    assert mock_db.execute.called
