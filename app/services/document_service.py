from io import BytesIO
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader
from docx import Document

DOCUMENT_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "text",
    "text/markdown": "markdown",
    "text/x-markdown": "markdown",
}


async def extract_document(file: UploadFile, max_bytes: int) -> tuple[str, str, int]:
    content_type = file.content_type or "application/octet-stream"
    extension = Path(file.filename or "").suffix.lower()
    kind = DOCUMENT_TYPES.get(content_type)
    if not kind and extension in {".md", ".markdown"}:
        kind = "markdown"
    if not kind and extension == ".txt":
        kind = "text"
    if not kind:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Use PDF, DOCX, Markdown, or plain text")

    raw = await file.read(max_bytes + 1)
    await file.seek(0)
    if len(raw) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Document is too large")

    try:
        if kind == "pdf":
            text = "\n\n".join((page.extract_text() or "").strip() for page in PdfReader(BytesIO(raw)).pages)
        elif kind == "docx":
            document = Document(BytesIO(raw))
            text = "\n".join(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())
        else:
            text = raw.decode("utf-8-sig")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Document text extraction failed") from exc

    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="No extractable text was found in the document")
    return normalized, kind, len(raw)
