from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from ..database import get_db
from ..dependencies import require_admin
from ..models import PROJECTS, doc_out, utcnow
from ..schemas import ProjectOut, ProjectPatch, ProjectWrite
from ..services.knowledge_refresh import refresh_source_task
from ..services.media_resolver import with_cover

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(featured: bool | None = None, db: Database = Depends(get_db)):
    query: dict = {"published": True}
    if featured is not None:
        query["featured"] = featured
    projects = db[PROJECTS].find(query).sort([("sort_order", 1), ("_id", 1)])
    return [with_cover(db, item) for item in projects]


@router.get("/admin", response_model=list[ProjectOut], dependencies=[Depends(require_admin)])
def list_all_projects(db: Database = Depends(get_db)):
    projects = db[PROJECTS].find().sort([("sort_order", 1), ("_id", 1)])
    return [with_cover(db, item) for item in projects]


@router.get("/admin/{slug}", response_model=ProjectOut, dependencies=[Depends(require_admin)])
def get_project_admin(slug: str, db: Database = Depends(get_db)):
    project = db[PROJECTS].find_one({"slug": slug})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return with_cover(db, project)


@router.get("/{slug}", response_model=ProjectOut)
def get_project(slug: str, db: Database = Depends(get_db)):
    project = db[PROJECTS].find_one({"slug": slug, "published": True})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return with_cover(db, project)


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_project(payload: ProjectWrite, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    now = utcnow()
    data = payload.model_dump()
    data["created_at"] = data["updated_at"] = now
    try:
        result = db[PROJECTS].insert_one(data)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Project slug already exists")
    tasks.add_task(refresh_source_task, "project")
    return doc_out(db[PROJECTS].find_one({"_id": result.inserted_id}))


@router.patch("/{slug}", response_model=ProjectOut, dependencies=[Depends(require_admin)])
def update_project(slug: str, payload: ProjectPatch, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_at"] = utcnow()
    result = db[PROJECTS].update_one({"slug": slug}, {"$set": changes})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks.add_task(refresh_source_task, "project")
    return doc_out(db[PROJECTS].find_one({"slug": slug}))


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_project(slug: str, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    result = db[PROJECTS].delete_one({"slug": slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    tasks.add_task(refresh_source_task, "project")
