from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..models import PROFILES, doc_out, utcnow
from ..schemas import ProfileOut, ProfileWrite
from ..services.knowledge_refresh import refresh_source_task

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileOut)
def get_profile(db: Database = Depends(get_db)):
    profile = db[PROFILES].find_one()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not configured")
    return doc_out(profile)


@router.put("", response_model=ProfileOut, dependencies=[Depends(require_admin)])
def upsert_profile(payload: ProfileWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    existing = db[PROFILES].find_one()
    now = utcnow()
    data = payload.model_dump()
    if existing:
        data["updated_at"] = now
        db[PROFILES].update_one({"_id": existing["_id"]}, {"$set": data})
        profile = db[PROFILES].find_one({"_id": existing["_id"]})
    else:
        data["created_at"] = data["updated_at"] = now
        result = db[PROFILES].insert_one(data)
        profile = db[PROFILES].find_one({"_id": result.inserted_id})
    tasks.add_task(refresh_source_task, "profile")
    return doc_out(profile)
