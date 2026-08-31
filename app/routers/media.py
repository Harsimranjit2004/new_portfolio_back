from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..models import FIELD_NOTES, MEDIA_ASSETS, PROFILES, PROJECTS, doc_out, utcnow
from ..schemas import MediaOut
from ..services.media_service import delete_upload, save_upload

router = APIRouter(prefix="/media-assets", tags=["media"])


def object_id_or_404(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Media asset not found") from exc


@router.get("", response_model=list[MediaOut], dependencies=[Depends(require_admin)])
def list_media(db: Database = Depends(get_db)):
    assets = db[MEDIA_ASSETS].find().sort("created_at", -1)
    return [doc_out(item) for item in assets]


@router.post("", response_model=MediaOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def upload_media(
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
    caption: str | None = Form(None),
    purpose: str = Form("general", pattern=r"^(general|profile|about|project|field_note)$"),
    related_project: str | None = Form(None),
    db: Database = Depends(get_db),
):
    key, url, size = await save_upload(file)
    kind = "image" if (file.content_type or "").startswith("image/") else "video" if (file.content_type or "").startswith("video/") else "document"
    now = utcnow()
    doc = {
        "filename": file.filename or key, "storage_key": key, "public_url": url,
        "mime_type": file.content_type or "application/octet-stream", "size_bytes": size,
        "alt_text": alt_text, "caption": caption, "kind": kind, "purpose": purpose,
        "related_project": related_project or None, "extra": {},
        "created_at": now, "updated_at": now,
    }
    result = db[MEDIA_ASSETS].insert_one(doc)
    return doc_out(db[MEDIA_ASSETS].find_one({"_id": result.inserted_id}))


@router.patch("/{asset_id}", response_model=MediaOut, dependencies=[Depends(require_admin)])
def update_media(asset_id: str, alt_text: str | None = None, caption: str | None = None, db: Database = Depends(get_db)):
    oid = object_id_or_404(asset_id)
    changes = {"updated_at": utcnow()}
    if alt_text is not None:
        changes["alt_text"] = alt_text
    if caption is not None:
        changes["caption"] = caption
    result = db[MEDIA_ASSETS].update_one({"_id": oid}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Media asset not found")
    return doc_out(db[MEDIA_ASSETS].find_one({"_id": oid}))


@router.delete("/{asset_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_media(asset_id: str, db: Database = Depends(get_db)):
    oid = object_id_or_404(asset_id)
    asset = db[MEDIA_ASSETS].find_one({"_id": oid})
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    references = []
    if db[PROFILES].find_one({"avatar_media_id": asset_id}):
        references.append("profile avatar")
    project = db[PROJECTS].find_one({"cover_media_id": asset_id})
    if project:
        references.append(f"project {project.get('title', project.get('slug', ''))}")
    note = db[FIELD_NOTES].find_one({"cover_media_id": asset_id})
    if note:
        references.append(f"Field Note {note.get('title', note.get('slug', ''))}")
    if references:
        raise HTTPException(status_code=409, detail=f"Media is in use by {', '.join(references)}")
    delete_upload(asset["storage_key"])
    db[MEDIA_ASSETS].delete_one({"_id": oid})
