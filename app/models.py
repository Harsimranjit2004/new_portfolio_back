from datetime import datetime, timezone
from typing import Any

PROFILES = "profiles"
SITE_SETTINGS = "site_settings"
PAGE_CONTENTS = "page_contents"
PROJECTS = "projects"
FIELD_NOTES = "field_notes"
MEDIA_ASSETS = "media_assets"
KNOWLEDGE_DOCUMENTS = "knowledge_documents"
KNOWLEDGE_CHUNKS = "knowledge_chunks"
KNOWLEDGE_UPLOADS = "knowledge_uploads"
KNOWLEDGE_ENTITIES = "knowledge_entities"
KNOWLEDGE_RELATIONSHIPS = "knowledge_relationships"
CONTACT_SUBMISSIONS = "contact_submissions"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def doc_out(doc: dict[str, Any]) -> dict[str, Any]:
    """Convert a Mongo document (with _id) into an API-shaped dict (with id: str)."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc
