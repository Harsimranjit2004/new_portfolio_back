import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from ..database import get_db
from ..dependencies import require_admin
from ..models import FIELD_NOTES, doc_out, utcnow
from ..schemas import FieldNoteOut, FieldNotePatch, FieldNoteWrite
from ..services.knowledge_refresh import refresh_source_task

router = APIRouter(prefix="/field-notes", tags=["field-notes"])


@router.get("", response_model=list[FieldNoteOut])
def list_notes(tag: str | None = None, project: str | None = None, search: str | None = None, limit: int = Query(50, ge=1, le=100), db: Database = Depends(get_db)):
    query: dict = {"published": True}
    if project:
        query["project_slug"] = project
    if search:
        pattern = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [{"title": pattern}, {"excerpt": pattern}, {"body": pattern}]
    notes = list(db[FIELD_NOTES].find(query).sort([("published_at", -1), ("_id", -1)]).limit(limit))
    return [doc_out(note) for note in notes if not tag or tag in (note.get("tags") or [])]


@router.get("/admin", response_model=list[FieldNoteOut], dependencies=[Depends(require_admin)])
def list_all_notes(db: Database = Depends(get_db)):
    notes = db[FIELD_NOTES].find().sort([("published_at", -1), ("_id", -1)])
    return [doc_out(note) for note in notes]


@router.get("/admin/{slug}", response_model=FieldNoteOut, dependencies=[Depends(require_admin)])
def get_note_admin(slug: str, db: Database = Depends(get_db)):
    note = db[FIELD_NOTES].find_one({"slug": slug})
    if not note:
        raise HTTPException(status_code=404, detail="Field note not found")
    return doc_out(note)


@router.get("/{slug}", response_model=FieldNoteOut)
def get_note(slug: str, db: Database = Depends(get_db)):
    note = db[FIELD_NOTES].find_one({"slug": slug, "published": True})
    if not note:
        raise HTTPException(status_code=404, detail="Field note not found")
    return doc_out(note)


@router.post("", response_model=FieldNoteOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_note(payload: FieldNoteWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    now = utcnow()
    data = payload.model_dump()
    data["created_at"] = data["updated_at"] = now
    try:
        result = db[FIELD_NOTES].insert_one(data)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Field note slug already exists")
    tasks.add_task(refresh_source_task, "field_note")
    return doc_out(db[FIELD_NOTES].find_one({"_id": result.inserted_id}))


@router.patch("/{slug}", response_model=FieldNoteOut, dependencies=[Depends(require_admin)])
def update_note(slug: str, payload: FieldNotePatch, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = utcnow()
    result = db[FIELD_NOTES].update_one({"slug": slug}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Field note not found")
    tasks.add_task(refresh_source_task, "field_note")
    return doc_out(db[FIELD_NOTES].find_one({"slug": slug}))


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_note(slug: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    result = db[FIELD_NOTES].delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Field note not found")
    tasks.add_task(refresh_source_task, "field_note")
