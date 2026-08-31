import hashlib
from typing import Annotated

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pymongo.database import Database

from ..config import get_settings
from ..database import get_db
from ..dependencies import require_admin
from ..models import KNOWLEDGE_CHUNKS, KNOWLEDGE_DOCUMENTS, KNOWLEDGE_UPLOADS, doc_out, utcnow
from ..schemas import KnowledgeUploadOut, KnowledgeUploadPatch
from ..services.document_service import extract_document
from ..services.knowledge_refresh import refresh_source_task
from ..services.media_service import delete_upload, save_upload

router = APIRouter(prefix="/knowledge-documents", tags=["knowledge-documents"], dependencies=[Depends(require_admin)])


def object_id_or_404(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Knowledge document not found") from exc


@router.get("", response_model=list[KnowledgeUploadOut])
def list_documents(db: Database = Depends(get_db)):
    return [doc_out(item) for item in db[KNOWLEDGE_UPLOADS].find().sort("created_at", -1)]


@router.post("", response_model=KnowledgeUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(min_length=1, max_length=240)],
    description: Annotated[str | None, Form()] = None,
    visibility: Annotated[str, Form(pattern=r"^(public|internal|private)$")] = "public",
    related_project: Annotated[str | None, Form()] = None,
    citation_label: Annotated[str | None, Form()] = None,
    db: Database = Depends(get_db),
):
    settings = get_settings()
    extracted_text, document_type, _ = await extract_document(file, settings.max_upload_mb * 1024 * 1024)
    storage_key, public_url, size = await save_upload(file)
    now = utcnow()
    document = {
        "title": title.strip(), "description": description, "filename": file.filename or storage_key,
        "storage_key": storage_key, "public_url": public_url, "mime_type": file.content_type or "application/octet-stream",
        "size_bytes": size, "document_type": document_type, "visibility": visibility,
        "related_project": related_project or None, "citation_label": citation_label or None,
        "status": "ready", "error": None, "enabled": True, "extracted_text": extracted_text,
        "content_hash": hashlib.sha256(extracted_text.encode("utf-8")).hexdigest(), "chunk_count": 0,
        "indexed_at": None, "created_at": now, "updated_at": now,
    }
    try:
        result = db[KNOWLEDGE_UPLOADS].insert_one(document)
    except Exception:
        delete_upload(storage_key)
        raise
    tasks.add_task(refresh_source_task, "upload")
    return doc_out(db[KNOWLEDGE_UPLOADS].find_one({"_id": result.inserted_id}))


@router.patch("/{document_id}", response_model=KnowledgeUploadOut)
def update_document(document_id: str, payload: KnowledgeUploadPatch, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    oid = object_id_or_404(document_id)
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = utcnow()
    result = db[KNOWLEDGE_UPLOADS].update_one({"_id": oid}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    tasks.add_task(refresh_source_task, "upload")
    return doc_out(db[KNOWLEDGE_UPLOADS].find_one({"_id": oid}))


@router.post("/{document_id}/reindex", response_model=KnowledgeUploadOut)
def reindex_document(document_id: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    oid = object_id_or_404(document_id)
    result = db[KNOWLEDGE_UPLOADS].update_one({"_id": oid}, {"$set": {"status": "ready", "error": None, "updated_at": utcnow()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    tasks.add_task(refresh_source_task, "upload")
    return doc_out(db[KNOWLEDGE_UPLOADS].find_one({"_id": oid}))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    oid = object_id_or_404(document_id)
    upload = db[KNOWLEDGE_UPLOADS].find_one({"_id": oid})
    if not upload:
        raise HTTPException(status_code=404, detail="Knowledge document not found")
    knowledge = db[KNOWLEDGE_DOCUMENTS].find_one({"source_type": "upload", "source_id": str(oid)})
    if knowledge:
        db[KNOWLEDGE_CHUNKS].delete_many({"document_id": knowledge["_id"]})
        db[KNOWLEDGE_DOCUMENTS].delete_one({"_id": knowledge["_id"]})
    delete_upload(upload["storage_key"])
    db[KNOWLEDGE_UPLOADS].delete_one({"_id": oid})
    tasks.add_task(refresh_source_task, "upload")
