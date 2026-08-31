import asyncio

from bson import ObjectId

from ..config import get_settings
from ..database import get_db
from ..models import KNOWLEDGE_CHUNKS, KNOWLEDGE_DOCUMENTS, KNOWLEDGE_UPLOADS, utcnow
from .rag_pipeline import reindex


async def refresh_source(db, source_type: str) -> None:
    await reindex(db, source_types=[source_type], force=False)
    if source_type != "upload":
        return
    for document in db[KNOWLEDGE_DOCUMENTS].find({"source_type": "upload"}):
        try:
            upload_id = ObjectId(document["source_id"])
        except Exception:
            continue
        chunk_count = db[KNOWLEDGE_CHUNKS].count_documents({"document_id": document["_id"]})
        db[KNOWLEDGE_UPLOADS].update_one({"_id": upload_id}, {"$set": {
            "status": "indexed", "chunk_count": chunk_count, "indexed_at": utcnow(), "error": None,
        }})
    db[KNOWLEDGE_UPLOADS].update_many(
        {"$or": [{"visibility": {"$ne": "public"}}, {"enabled": False}]},
        {"$set": {"status": "ready", "chunk_count": 0, "indexed_at": None}},
    )


def refresh_source_task(source_type: str) -> None:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_embedding_model:
        return
    asyncio.run(refresh_source(get_db(), source_type))
