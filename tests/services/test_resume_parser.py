import pytest
import uuid
import os
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.resume import FileType
from app.models.candidate import CandidateProfile
from app.services.resume_service import process_resume_from_disk
from app.ai.text_extraction import extract_text

def test_extract_text_txt():
    content = b"This is a test resume."
    text = extract_text(content, "TXT")
    assert text == "This is a test resume."

def test_extract_text_unsupported():
    with pytest.raises(ValueError):
        extract_text(b"dummy", "PNG")

@patch("app.ai.text_extraction._extract_from_pdf")
def test_extract_text_pdf(mock_pdf):
    mock_pdf.return_value = "PDF text"
    text = extract_text(b"fake_pdf_bytes", "PDF")
    assert text == "PDF text"

@patch("app.ai.text_extraction._extract_from_docx")
def test_extract_text_docx(mock_docx):
    mock_docx.return_value = "DOCX text"
    text = extract_text(b"fake_docx_bytes", "DOCX")
    assert text == "DOCX text"

@pytest.mark.asyncio
async def test_process_resume_from_disk(tmp_path):
    # Create a temporary file
    test_file = tmp_path / "test_resume.txt"
    test_file.write_text("dummy resume text")
    
    db = AsyncMock()
    candidate_id = uuid.uuid4()
    
    # Mock CandidateProfile
    profile = CandidateProfile(
        id=candidate_id,
        user_id=uuid.uuid4(),
        first_name="",
        last_name=""
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = profile
    db.execute.return_value = mock_result
    
    resume = await process_resume_from_disk(
        str(test_file),
        "test_resume.txt",
        FileType.TXT,
        candidate_id,
        db
    )
    
    assert resume.file_name == "test_resume.txt"
    assert resume.file_type == FileType.TXT
    assert resume.raw_text == "dummy resume text"
    assert resume.parsed_data is not None
    assert profile.first_name == "Jane"  # From mock LLM
    assert profile.last_name == "Doe"
    assert db.add.called
    assert db.commit.called
