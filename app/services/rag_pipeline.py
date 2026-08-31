import hashlib
import math
import re
from dataclasses import dataclass

from pymongo.database import Database

from ..config import get_settings
from ..models import KNOWLEDGE_CHUNKS, KNOWLEDGE_DOCUMENTS, utcnow
from ..schemas import KnowledgeStatus, RAGSource, ReindexResponse
from .knowledge_builder import build_all
from .knowledge_graph import rebuild_graph
from .openai_service import OpenAICompatibleClient


@dataclass
class RetrievedChunk:
    content: str
    title: str
    url: str
    source_type: str
    score: float


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def chunk_text(content: str, size: int, overlap: int) -> list[str]:
    normalized = "\n".join(line.rstrip() for line in content.splitlines()).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + size)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n\n", start, end), normalized.rfind(". ", start, end))
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


async def reindex(db: Database, source_types: list[str] | None = None, force: bool = False) -> ReindexResponse:
    settings = get_settings()
    source_documents = build_all(db, source_types)
    seen_keys = {(doc.source_type, doc.source_id) for doc in source_documents}
    updated = unchanged = embedded = removed = 0
    client = OpenAICompatibleClient()

    for source in source_documents:
        digest = content_hash(source.content)
        document = db[KNOWLEDGE_DOCUMENTS].find_one({"source_type": source.source_type, "source_id": source.source_id})
        if document and document["content_hash"] == digest and not force:
            unchanged += 1
            continue
        now = utcnow()
        if not document:
            result = db[KNOWLEDGE_DOCUMENTS].insert_one({
                "source_type": source.source_type, "source_id": source.source_id, "title": source.title, "url": source.url,
                "content": source.content, "content_hash": digest, "metadata_json": source.metadata, "enabled": True,
                "created_at": now, "updated_at": now,
            })
            document_id = result.inserted_id
        else:
            document_id = document["_id"]
            db[KNOWLEDGE_DOCUMENTS].update_one({"_id": document_id}, {"$set": {
                "title": source.title, "url": source.url, "content": source.content, "content_hash": digest,
                "metadata_json": source.metadata, "enabled": True, "updated_at": now,
            }})
            db[KNOWLEDGE_CHUNKS].delete_many({"document_id": document_id})

        chunks = chunk_text(source.content, settings.rag_chunk_size, settings.rag_chunk_overlap)
        vectors: list[list[float]] = []
        for batch_start in range(0, len(chunks), 64):
            vectors.extend(await client.embed(chunks[batch_start:batch_start + 64]))
        chunk_docs = [{
            "document_id": document_id, "chunk_index": index, "content": chunk, "token_estimate": max(1, len(chunk) // 4),
            "embedding": vector, "embedding_model": settings.openai_embedding_model, "metadata_json": source.metadata,
            "created_at": now, "updated_at": now,
        } for index, (chunk, vector) in enumerate(zip(chunks, vectors))]
        if chunk_docs:
            db[KNOWLEDGE_CHUNKS].insert_many(chunk_docs)
        updated += 1
        embedded += len(chunks)

    query: dict = {}
    if source_types:
        query["source_type"] = {"$in": source_types}
    for document in list(db[KNOWLEDGE_DOCUMENTS].find(query)):
        if (document["source_type"], document["source_id"]) not in seen_keys:
            db[KNOWLEDGE_CHUNKS].delete_many({"document_id": document["_id"]})
            db[KNOWLEDGE_DOCUMENTS].delete_one({"_id": document["_id"]})
            removed += 1

    rebuild_graph(db)
    return ReindexResponse(documents_seen=len(source_documents), documents_updated=updated, documents_unchanged=unchanged, chunks_embedded=embedded, documents_removed=removed)


async def retrieve(db: Database, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    query_vector = (await OpenAICompatibleClient().embed([query]))[0]
    enabled_documents = {doc["_id"]: doc for doc in db[KNOWLEDGE_DOCUMENTS].find({"enabled": True})}
    ranked: list[RetrievedChunk] = []
    if enabled_documents:
        for chunk in db[KNOWLEDGE_CHUNKS].find({"document_id": {"$in": list(enabled_documents.keys())}}):
            if not chunk.get("embedding"):
                continue
            document = enabled_documents[chunk["document_id"]]
            semantic_score = cosine_similarity(query_vector, chunk["embedding"])
            query_terms = {term for term in re.findall(r"[a-z0-9+#.-]{3,}", query.lower()) if term not in {"which", "what", "where", "with", "that", "this", "work", "project"}}
            haystack = f"{document['title']} {chunk['content']}".lower()
            matched_terms = sum(1 for term in query_terms if term in haystack)
            lexical_boost = min(0.18, matched_terms * 0.035)
            ranked.append(RetrievedChunk(chunk["content"], document["title"], document["url"], document["source_type"], semantic_score + lexical_boost))
    ranked.sort(key=lambda item: item.score, reverse=True)
    selected = [item for item in ranked if item.score >= settings.rag_min_score][:top_k or settings.rag_top_k]
    return selected


def sources_from_chunks(chunks: list[RetrievedChunk]) -> list[RAGSource]:
    sources: list[RAGSource] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks:
        key = (chunk.title, chunk.url)
        if key in seen:
            continue
        seen.add(key)
        excerpt = chunk.content.replace("\n", " ")[:240].strip()
        sources.append(RAGSource(title=chunk.title, url=chunk.url, source_type=chunk.source_type, excerpt=excerpt, score=round(chunk.score, 4)))
    return sources


def knowledge_status(db: Database) -> KnowledgeStatus:
    settings = get_settings()
    documents = db[KNOWLEDGE_DOCUMENTS].count_documents({})
    chunks = db[KNOWLEDGE_CHUNKS].count_documents({})
    source_counts = {row["_id"]: row["count"] for row in db[KNOWLEDGE_DOCUMENTS].aggregate([{"$group": {"_id": "$source_type", "count": {"$sum": 1}}}])}
    return KnowledgeStatus(documents=documents, chunks=chunks, embedded_chunks=chunks, source_counts=source_counts, embedding_model=settings.openai_embedding_model)
