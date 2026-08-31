import hashlib

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..models import CONTACT_SUBMISSIONS, doc_out, utcnow
from ..schemas import ContactCreate, ContactOut, ContactStatusUpdate
from ..services.email_service import send_contact_email

router = APIRouter(prefix="/contact", tags=["contact"])


def object_id_or_404(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError) as exc:
        raise HTTPException(status_code=404, detail="Submission not found") from exc


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def submit_contact(payload: ContactCreate, request: Request, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    if payload.website:
        raise HTTPException(status_code=400, detail="Invalid submission")
    client_ip = request.client.host if request.client else "unknown"
    doc = {
        "name": payload.name, "email": str(payload.email), "topic": payload.topic, "message": payload.message,
        "status": "new", "source": "portfolio",
        "ip_hash": hashlib.sha256(client_ip.encode()).hexdigest(),
        "created_at": utcnow(),
    }
    result = db[CONTACT_SUBMISSIONS].insert_one(doc)
    tasks.add_task(send_contact_email, payload)
    return doc_out(db[CONTACT_SUBMISSIONS].find_one({"_id": result.inserted_id}))


@router.get("", response_model=list[ContactOut], dependencies=[Depends(require_admin)])
def list_submissions(status_filter: str | None = None, db: Database = Depends(get_db)):
    query: dict = {}
    if status_filter:
        query["status"] = status_filter
    submissions = db[CONTACT_SUBMISSIONS].find(query).sort("created_at", -1)
    return [doc_out(item) for item in submissions]


@router.patch("/{submission_id}", response_model=ContactOut, dependencies=[Depends(require_admin)])
def update_submission(submission_id: str, payload: ContactStatusUpdate, db: Database = Depends(get_db)):
    oid = object_id_or_404(submission_id)
    result = db[CONTACT_SUBMISSIONS].update_one({"_id": oid}, {"$set": {"status": payload.status}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    return doc_out(db[CONTACT_SUBMISSIONS].find_one({"_id": oid}))


@router.delete("/{submission_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_submission(submission_id: str, db: Database = Depends(get_db)):
    oid = object_id_or_404(submission_id)
    result = db[CONTACT_SUBMISSIONS].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
