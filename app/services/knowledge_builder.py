import json
from dataclasses import dataclass, field
from typing import Any

from pymongo.database import Database

from ..models import FIELD_NOTES, KNOWLEDGE_UPLOADS, PAGE_CONTENTS, PROFILES, PROJECTS, SITE_SETTINGS


@dataclass
class SourceDocument:
    source_type: str
    source_id: str
    title: str
    url: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_profile(db: Database) -> list[SourceDocument]:
    profile = db[PROFILES].find_one()
    if not profile:
        return []
    content = "\n\n".join(filter(None, [
        f"Name: {profile.get('name', '')}", f"Role: {profile.get('role', '')}", f"Location: {profile.get('location') or ''}",
        profile.get("headline") or "", profile.get("biography") or "", "Working set:\n" + text(profile.get("working_set")),
        "Currently:\n" + text(profile.get("currently")), "Social links:\n" + text(profile.get("social_links")), text(profile.get("extra")),
    ]))
    return [SourceDocument("profile", str(profile["_id"]), f"About {profile.get('name', '')}", "/about", content, {"role": profile.get("role")})]


def build_projects(db: Database) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for project in db[PROJECTS].find({"published": True}):
        content = "\n\n".join(filter(None, [
            f"Project: {project.get('title', '')}", f"Domain: {project.get('domain', '')}", f"Status: {project.get('status', '')}",
            project.get("question") or "", project.get("thesis") or "", project.get("summary") or "",
            "Metrics:\n" + text(project.get("metrics")), "Pipeline:\n" + text(project.get("pipeline")),
            "Execution trace:\n" + text(project.get("trace")), "Case study sections:\n" + text(project.get("sections")),
            "Technologies: " + ", ".join(project.get("technologies") or []), "Links:\n" + text(project.get("links")), text(project.get("extra")),
        ]))
        docs.append(SourceDocument("project", project["slug"], project["title"], f"/work/{project['slug']}", content, {"domain": project.get("domain"), "status": project.get("status"), "technologies": project.get("technologies")}))
    return docs


def build_field_notes(db: Database) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for note in db[FIELD_NOTES].find({"published": True}):
        tags = note.get("tags") or []
        content = "\n\n".join(filter(None, [
            f"Field note: {note.get('title', '')}", f"Type: {note.get('note_type', '')}", f"Tags: {', '.join(tags)}",
            note.get("excerpt", ""), note.get("body", ""), "Structured content:\n" + text(note.get("content_blocks")),
        ]))
        docs.append(SourceDocument("field_note", note["slug"], note["title"], f"/field-notes/{note['slug']}", content, {"tags": tags, "project_slug": note.get("project_slug"), "note_type": note.get("note_type")}))
    return docs


def build_pages(db: Database) -> list[SourceDocument]:
    grouped: dict[str, list[dict]] = {}
    for section in db[PAGE_CONTENTS].find({"enabled": True}).sort([("page", 1), ("sort_order", 1)]):
        grouped.setdefault(section["page"], []).append(section)
    return [SourceDocument("page", page, f"{page.title()} page", "/" if page == "home" else f"/{page}", "\n\n".join(f"{item['section']}:\n{text(item.get('content'))}" for item in sections), {"sections": [item["section"] for item in sections]}) for page, sections in grouped.items()]


def build_settings(db: Database) -> list[SourceDocument]:
    settings = list(db[SITE_SETTINGS].find({"is_public": True}))
    if not settings:
        return []
    content = "\n\n".join(f"{item['key']}:\n{text(item.get('value'))}" for item in settings)
    return [SourceDocument("site", "public-settings", "Portfolio site information", "/", content)]


def build_uploads(db: Database) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    query = {"visibility": "public", "enabled": True, "status": {"$in": ["ready", "indexed"]}}
    for upload in db[KNOWLEDGE_UPLOADS].find(query):
        title = upload.get("citation_label") or upload.get("title") or upload.get("filename") or "Portfolio document"
        description = upload.get("description") or ""
        related = upload.get("related_project")
        content = "\n\n".join(filter(None, [
            f"Document: {upload.get('title', '')}",
            f"Related project: {related}" if related else "",
            description,
            upload.get("extracted_text") or "",
        ]))
        docs.append(SourceDocument(
            "upload", str(upload["_id"]), title, upload.get("public_url") or "/about", content,
            {"document_type": upload.get("document_type"), "related_project": related, "visibility": "public"},
        ))
    return docs


BUILDERS = {"profile": build_profile, "project": build_projects, "field_note": build_field_notes, "page": build_pages, "site": build_settings, "upload": build_uploads}


def build_all(db: Database, source_types: list[str] | None = None) -> list[SourceDocument]:
    selected = source_types or list(BUILDERS)
    unknown = set(selected) - set(BUILDERS)
    if unknown:
        raise ValueError(f"Unknown source types: {', '.join(sorted(unknown))}")
    documents: list[SourceDocument] = []
    for source_type in selected:
        documents.extend(BUILDERS[source_type](db))
    return documents
