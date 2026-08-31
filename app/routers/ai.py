from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..models import KNOWLEDGE_CHUNKS, KNOWLEDGE_DOCUMENTS, doc_out, utcnow
from ..schemas import AIChatRequest, AIChatResponse, KnowledgeDocumentOut, KnowledgeStatus, ReindexRequest, ReindexResponse
from ..services.ai_service import answer_portfolio_question
from ..services.rag_pipeline import knowledge_status, reindex

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AIChatResponse)
async def chat(payload: AIChatRequest, db: Database = Depends(get_db)):
    return await answer_portfolio_question(db, payload)


@router.post("/reindex", response_model=ReindexResponse, dependencies=[Depends(require_admin)])
async def rebuild_knowledge(payload: ReindexRequest, db: Database = Depends(get_db)):
    try:
        return await reindex(db, source_types=payload.source_types, force=payload.force)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", response_model=KnowledgeStatus, dependencies=[Depends(require_admin)])
def rag_status(db: Database = Depends(get_db)):
    return knowledge_status(db)


@router.get("/sources", response_model=list[KnowledgeDocumentOut], dependencies=[Depends(require_admin)])
def rag_sources(db: Database = Depends(get_db)):
    documents = db[KNOWLEDGE_DOCUMENTS].find().sort([("source_type", 1), ("title", 1)])
    return [doc_out(item) for item in documents]


@router.patch("/sources/{document_id}/toggle", response_model=KnowledgeDocumentOut, dependencies=[Depends(require_admin)])
def toggle_source(document_id: str, db: Database = Depends(get_db)):
    try:
        oid = ObjectId(document_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Knowledge source not found") from exc
    document = db[KNOWLEDGE_DOCUMENTS].find_one({"_id": oid})
    if not document:
        raise HTTPException(status_code=404, detail="Knowledge source not found")
    db[KNOWLEDGE_DOCUMENTS].update_one({"_id": oid}, {"$set": {"enabled": not document["enabled"], "updated_at": utcnow()}})
    return doc_out(db[KNOWLEDGE_DOCUMENTS].find_one({"_id": oid}))


@router.delete("/index", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def clear_index(db: Database = Depends(get_db)):
    db[KNOWLEDGE_CHUNKS].delete_many({})
    db[KNOWLEDGE_DOCUMENTS].delete_many({})
