from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import ensure_indexes, get_db
from .routers import admin_assistant, ai, auth, contact, field_notes, health, knowledge, media, profile, projects, site
from .services.seed_service import seed_defaults

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = get_db()
    ensure_indexes(db)
    seed_defaults(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Content, media, contact, and AI API for the engineering portfolio.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/media", StaticFiles(directory=str(settings.upload_path)), name="media")

api_prefix = "/api/v1"
for router in (health.router, auth.router, profile.router, site.router, projects.router, field_notes.router, media.router, knowledge.router, contact.router, ai.router, admin_assistant.router):
    app.include_router(router, prefix=api_prefix)


@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": f"{api_prefix}/health"}
