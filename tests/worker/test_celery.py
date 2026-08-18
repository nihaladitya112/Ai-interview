import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from app.worker import process_resume_task, ingest_document_task, generate_interview_report_task

@patch("app.worker.process_resume_from_disk", new_callable=AsyncMock)
@patch("app.worker.AsyncSessionLocal")
def test_process_resume_task(mock_session, mock_process):
    mock_resume = MagicMock()
    mock_resume.id = uuid.uuid4()
    mock_process.return_value = mock_resume
    
    mock_db = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_db
    
    res = process_resume_task(
        file_path="dummy.txt", 
        filename="dummy.txt", 
        file_type_str="TXT", 
        candidate_id_str=str(uuid.uuid4()), 
        file_id_str=str(uuid.uuid4())
    )
    
    assert res["resume_id"] == str(mock_resume.id)

@patch("app.worker.ingest_document", new_callable=AsyncMock)
@patch("app.worker.AsyncSessionLocal")
def test_ingest_document_task(mock_session, mock_ingest):
    doc_id = uuid.uuid4()
    mock_ingest.return_value = (doc_id, 3)
    
    mock_db = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_db
    
    res = ingest_document_task(
        domain="Python", 
        title="Doc", 
        content="Content"
    )
    
    assert res["document_id"] == str(doc_id)
    assert res["chunks_created"] == 3

@patch("app.worker.generate_interview_report", new_callable=AsyncMock)
@patch("app.worker.AsyncSessionLocal")
def test_generate_interview_report_task(mock_session, mock_gen):
    report = MagicMock()
    report.id = uuid.uuid4()
    report.overall_score = 8.5
    mock_gen.return_value = report
    
    mock_db = AsyncMock()
    mock_session.return_value.__aenter__.return_value = mock_db
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    mock_db.execute.return_value = mock_result
    
    res = generate_interview_report_task(str(uuid.uuid4()))
    
    assert res["report_id"] == str(report.id)
    assert res["overall_score"] == 8.5
