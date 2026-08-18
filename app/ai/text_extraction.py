import io
import pypdf
import docx

def extract_text(file_bytes: bytes, file_type: str) -> str:
    ext = file_type.upper()
    if ext == "PDF":
        return _extract_from_pdf(file_bytes)
    elif ext == "DOCX":
        return _extract_from_docx(file_bytes)
    elif ext == "TXT":
        return file_bytes.decode("utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def _extract_from_pdf(file_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()

def _extract_from_docx(file_bytes: bytes) -> str:
    doc = docx.Document(io.BytesIO(file_bytes))
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()
