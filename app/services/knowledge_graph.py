from pymongo import UpdateOne
from pymongo.database import Database

from ..models import (
    FIELD_NOTES, KNOWLEDGE_ENTITIES, KNOWLEDGE_RELATIONSHIPS, KNOWLEDGE_UPLOADS, PROFILES, PROJECTS, utcnow,
)


def _key(kind: str, value: str) -> str:
    return f"{kind}:{value.strip().lower().replace(' ', '-')}"


def rebuild_graph(db: Database) -> tuple[int, int]:
    now = utcnow()
    entities: dict[str, dict] = {}
    relationships: dict[tuple[str, str, str], dict] = {}

    def entity(kind: str, value: str, name: str | None = None, url: str | None = None, public: bool = True) -> str:
        key = _key(kind, value)
        entities[key] = {"key": key, "type": kind, "name": name or value, "url": url, "public": public, "updated_at": now}
        return key

    def relate(source: str, relation: str, target: str, source_id: str, public: bool = True) -> None:
        relationships[(source, relation, target)] = {
            "from": source, "relation": relation, "to": target, "source_id": source_id,
            "confidence": 1.0, "public": public, "updated_at": now,
        }

    profile = db[PROFILES].find_one()
    person = entity("person", str(profile.get("name", "harsimranjit")) if profile else "harsimranjit", profile.get("name") if profile else "Harsimranjit", "/about")

    for project in db[PROJECTS].find({"published": True}):
        project_key = entity("project", project["slug"], project.get("title"), f"/work/{project['slug']}")
        relate(person, "BUILT", project_key, project["slug"])
        if project.get("domain"):
            domain = entity("domain", project["domain"], project["domain"], "/work")
            relate(project_key, "BELONGS_TO", domain, project["slug"])
        for technology in project.get("technologies") or []:
            technology_key = entity("technology", technology, technology, "/work")
            relate(project_key, "USES", technology_key, project["slug"])

    for note in db[FIELD_NOTES].find({"published": True}):
        note_key = entity("field_note", note["slug"], note.get("title"), f"/field-notes/{note['slug']}")
        if note.get("project_slug"):
            project_key = entity("project", note["project_slug"], note["project_slug"], f"/work/{note['project_slug']}")
            relate(note_key, "EXPLAINS", project_key, note["slug"])

    for upload in db[KNOWLEDGE_UPLOADS].find({"visibility": "public", "enabled": True}):
        upload_key = entity("document", str(upload["_id"]), upload.get("title"), upload.get("public_url"))
        if upload.get("related_project"):
            project_key = entity("project", upload["related_project"], upload["related_project"], f"/work/{upload['related_project']}")
            relate(upload_key, "SUPPORTS", project_key, str(upload["_id"]))

    if entities:
        db[KNOWLEDGE_ENTITIES].bulk_write([UpdateOne({"key": key}, {"$set": value, "$setOnInsert": {"created_at": now}}, upsert=True) for key, value in entities.items()])
    db[KNOWLEDGE_ENTITIES].delete_many({"key": {"$nin": list(entities)}})
    db[KNOWLEDGE_RELATIONSHIPS].delete_many({})
    if relationships:
        db[KNOWLEDGE_RELATIONSHIPS].insert_many(list(relationships.values()))
    return len(entities), len(relationships)
