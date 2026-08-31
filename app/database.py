from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from .config import get_settings
from .models import (
    FIELD_NOTES, KNOWLEDGE_DOCUMENTS, KNOWLEDGE_ENTITIES, KNOWLEDGE_RELATIONSHIPS, KNOWLEDGE_UPLOADS, MEDIA_ASSETS, PROJECTS, SITE_SETTINGS,
)

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(get_settings().mongodb_uri)
    return _client


def get_db() -> Database:
    return get_client().get_default_database()


def ensure_indexes(db: Database) -> None:
    db[SITE_SETTINGS].create_index([("key", ASCENDING)], unique=True)
    db[PROJECTS].create_index([("slug", ASCENDING)], unique=True)
    db[FIELD_NOTES].create_index([("slug", ASCENDING)], unique=True)
    db[MEDIA_ASSETS].create_index([("storage_key", ASCENDING)], unique=True)
    db[KNOWLEDGE_ENTITIES].create_index([("key", ASCENDING)], unique=True)
    db[KNOWLEDGE_RELATIONSHIPS].create_index([("from", ASCENDING), ("relation", ASCENDING), ("to", ASCENDING)], unique=True)
    db[KNOWLEDGE_UPLOADS].create_index([("storage_key", ASCENDING)], unique=True)
    db[KNOWLEDGE_DOCUMENTS].create_index([("source_type", ASCENDING), ("source_id", ASCENDING)], unique=True)
