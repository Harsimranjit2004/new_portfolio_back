from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..models import PAGE_CONTENTS, SITE_SETTINGS, doc_out, utcnow
from ..schemas import PageContentOut, PageContentWrite, SiteSettingOut, SiteSettingWrite
from ..services.knowledge_refresh import refresh_source_task

router = APIRouter(prefix="/site", tags=["site-content"])


def object_id_or_404(raw_id: str, detail: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail=detail) from exc


@router.get("/settings", response_model=list[SiteSettingOut])
def public_settings(db: Database = Depends(get_db)):
    settings = db[SITE_SETTINGS].find({"is_public": True}).sort("key", 1)
    return [doc_out(item) for item in settings]


@router.put("/settings/{key}", response_model=SiteSettingOut, dependencies=[Depends(require_admin)])
def upsert_setting(key: str, payload: SiteSettingWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    now = utcnow()
    existing = db[SITE_SETTINGS].find_one({"key": key})
    data = payload.model_dump()
    if existing:
        data["updated_at"] = now
        db[SITE_SETTINGS].update_one({"_id": existing["_id"]}, {"$set": data})
        setting = db[SITE_SETTINGS].find_one({"_id": existing["_id"]})
    else:
        data.update(key=key, created_at=now, updated_at=now)
        result = db[SITE_SETTINGS].insert_one(data)
        setting = db[SITE_SETTINGS].find_one({"_id": result.inserted_id})
    tasks.add_task(refresh_source_task, "site")
    return doc_out(setting)


@router.delete("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_setting(key: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    result = db[SITE_SETTINGS].delete_one({"key": key})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Setting not found")
    tasks.add_task(refresh_source_task, "site")


@router.get("/pages/{page}", response_model=list[PageContentOut])
def page_content(page: str, db: Database = Depends(get_db)):
    sections = db[PAGE_CONTENTS].find({"page": page, "enabled": True}).sort([("sort_order", 1), ("_id", 1)])
    return [doc_out(item) for item in sections]


@router.get("/pages/{page}/admin", response_model=list[PageContentOut], dependencies=[Depends(require_admin)])
def page_content_admin(page: str, db: Database = Depends(get_db)):
    sections = db[PAGE_CONTENTS].find({"page": page}).sort([("sort_order", 1), ("_id", 1)])
    return [doc_out(item) for item in sections]


@router.post("/pages", response_model=PageContentOut, status_code=201, dependencies=[Depends(require_admin)])
def create_page_section(payload: PageContentWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    now = utcnow()
    data = payload.model_dump()
    data["created_at"] = data["updated_at"] = now
    result = db[PAGE_CONTENTS].insert_one(data)
    section = db[PAGE_CONTENTS].find_one({"_id": result.inserted_id})
    tasks.add_task(refresh_source_task, "page")
    return doc_out(section)


@router.put("/pages/{section_id}", response_model=PageContentOut, dependencies=[Depends(require_admin)])
def update_page_section(section_id: str, payload: PageContentWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    oid = object_id_or_404(section_id, "Page section not found")
    data = payload.model_dump()
    data["updated_at"] = utcnow()
    result = db[PAGE_CONTENTS].update_one({"_id": oid}, {"$set": data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Page section not found")
    section = db[PAGE_CONTENTS].find_one({"_id": oid})
    tasks.add_task(refresh_source_task, "page")
    return doc_out(section)


@router.delete("/pages/{section_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_page_section(section_id: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    oid = object_id_or_404(section_id, "Page section not found")
    result = db[PAGE_CONTENTS].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Page section not found")
    tasks.add_task(refresh_source_task, "page")
