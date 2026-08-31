import json
import re
from typing import Any

from fastapi import HTTPException
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from ..models import FIELD_NOTES, PAGE_CONTENTS, PROFILES, PROJECTS, SITE_SETTINGS, doc_out, utcnow
from ..schemas import (
    ContentAssistantRequest, ContentAssistantResponse, ContentProposal, ExecuteProposalResponse,
    FieldNotePatch, FieldNoteWrite, PageContentWrite, ProfileWrite, ProjectPatch, ProjectWrite, SiteSettingWrite,
)
from .openai_service import OpenAICompatibleClient

ACTIONS = "create_field_note, update_field_note, create_project, update_project, update_profile, upsert_setting, create_page_section"


def portfolio_context(db: Database) -> str:
    projects = list(db[PROJECTS].find({}, {"slug": 1, "title": 1, "status": 1}))
    notes = list(db[FIELD_NOTES].find({}, {"slug": 1, "title": 1, "tags": 1}))
    return json.dumps({
        "projects": [{"slug": p["slug"], "title": p["title"], "status": p["status"]} for p in projects],
        "field_notes": [{"slug": n["slug"], "title": n["title"], "tags": n.get("tags", [])} for n in notes],
    }, ensure_ascii=False)


def clean_json(content: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Content assistant returned invalid structured data") from exc


async def plan_content(db: Database, request: ContentAssistantRequest) -> ContentAssistantResponse:
    context = portfolio_context(db)
    system = f"""You are the private content copilot for Harsimranjit's engineering portfolio.
Turn the administrator's request into either a helpful clarification message or one safe structured proposal.
Allowed actions: {ACTIONS}.
Never propose deletion. Never publish unless the user explicitly asks. Never invent employers, credentials, production usage, or metrics.
Field Notes should be concise, technical, evidence-driven, and use the author's voice. Default new notes/projects to published=false and cover_media_id=null.
If a photo is unavailable, leave cover_media_id null; the frontend already provides the correct visual fallback.
Return JSON only with this exact shape:
{{"message":"...","proposal":null}}
or
{{"message":"...","proposal":{{"action":"create_field_note","summary":"...","payload":{{...}},"warnings":[]}}}}
For create_field_note include: slug,title,excerpt,body,note_type,tags,project_slug,reading_minutes,published_at,published,featured,cover_media_id,content_blocks,seo.
For update_field_note payload must include slug and changes.
For create_project include all required ProjectWrite fields.
For update_project payload must include slug and changes.
For update_profile provide fields to merge into the existing profile.
For upsert_setting payload must include key,value,description,is_public.
For create_page_section include page,section,sort_order,enabled,content.
Current records: {context}
"""
    history = [{"role": item.role, "content": item.content} for item in request.history[-8:]]
    raw = await OpenAICompatibleClient().chat([{"role": "system", "content": system}, *history, {"role": "user", "content": request.message}])
    parsed = clean_json(raw)
    return ContentAssistantResponse.model_validate(parsed)


def execute_content_proposal(db: Database, proposal: ContentProposal) -> tuple[ExecuteProposalResponse, str]:
    action, payload = proposal.action, proposal.payload
    now = utcnow()

    if action == "create_field_note":
        data = FieldNoteWrite.model_validate(payload).model_dump()
        data["created_at"] = data["updated_at"] = now
        try:
            result = db[FIELD_NOTES].insert_one(data)
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="A record with that slug already exists")
        record = db[FIELD_NOTES].find_one({"_id": result.inserted_id})
        return ExecuteProposalResponse(action=action, record_id=record["slug"], message=f"Created Field Note draft: {record['title']}"), "field_note"

    if action == "update_field_note":
        slug = str(payload.get("slug", ""))
        if not db[FIELD_NOTES].find_one({"slug": slug}):
            raise HTTPException(status_code=404, detail="Field Note not found")
        changes = FieldNotePatch.model_validate(payload.get("changes", {})).model_dump(exclude_unset=True)
        changes["updated_at"] = now
        db[FIELD_NOTES].update_one({"slug": slug}, {"$set": changes})
        record = db[FIELD_NOTES].find_one({"slug": slug})
        return ExecuteProposalResponse(action=action, record_id=record["slug"], message=f"Updated Field Note: {record['title']}"), "field_note"

    if action == "create_project":
        data = ProjectWrite.model_validate(payload).model_dump()
        data["created_at"] = data["updated_at"] = now
        try:
            result = db[PROJECTS].insert_one(data)
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="A record with that slug already exists")
        record = db[PROJECTS].find_one({"_id": result.inserted_id})
        return ExecuteProposalResponse(action=action, record_id=record["slug"], message=f"Created project draft: {record['title']}"), "project"

    if action == "update_project":
        slug = str(payload.get("slug", ""))
        if not db[PROJECTS].find_one({"slug": slug}):
            raise HTTPException(status_code=404, detail="Project not found")
        changes = ProjectPatch.model_validate(payload.get("changes", {})).model_dump(exclude_unset=True)
        changes["updated_at"] = now
        db[PROJECTS].update_one({"slug": slug}, {"$set": changes})
        record = db[PROJECTS].find_one({"slug": slug})
        return ExecuteProposalResponse(action=action, record_id=record["slug"], message=f"Updated project: {record['title']}"), "project"

    if action == "update_profile":
        existing = db[PROFILES].find_one()
        current = {k: v for k, v in (existing or {}).items() if k not in {"_id", "created_at", "updated_at"}}
        data = ProfileWrite.model_validate({**current, **payload}).model_dump()
        if not existing:
            data["created_at"] = data["updated_at"] = now
            result = db[PROFILES].insert_one(data)
            record = db[PROFILES].find_one({"_id": result.inserted_id})
        else:
            data["updated_at"] = now
            db[PROFILES].update_one({"_id": existing["_id"]}, {"$set": data})
            record = db[PROFILES].find_one({"_id": existing["_id"]})
        return ExecuteProposalResponse(action=action, record_id=str(record["_id"]), message="Updated public profile"), "profile"

    if action == "upsert_setting":
        key = str(payload.get("key", ""))
        data = SiteSettingWrite.model_validate({k: v for k, v in payload.items() if k != "key"}).model_dump()
        existing = db[SITE_SETTINGS].find_one({"key": key})
        if not existing:
            data.update(key=key, created_at=now, updated_at=now)
            db[SITE_SETTINGS].insert_one(data)
        else:
            data["updated_at"] = now
            db[SITE_SETTINGS].update_one({"_id": existing["_id"]}, {"$set": data})
        record = db[SITE_SETTINGS].find_one({"key": key})
        return ExecuteProposalResponse(action=action, record_id=record["key"], message=f"Updated site setting: {record['key']}"), "site"

    if action == "create_page_section":
        data = PageContentWrite.model_validate(payload).model_dump()
        data["created_at"] = data["updated_at"] = now
        result = db[PAGE_CONTENTS].insert_one(data)
        record = doc_out(db[PAGE_CONTENTS].find_one({"_id": result.inserted_id}))
        return ExecuteProposalResponse(action=action, record_id=record["id"], message=f"Created {record['page']}/{record['section']}"), "page"

    raise HTTPException(status_code=400, detail="Unsupported content action")
