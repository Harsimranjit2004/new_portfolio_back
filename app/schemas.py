from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=320)


class AdminLoginResponse(BaseModel):
    token: str
    expires_in: int


class SiteSettingWrite(BaseModel):
    value: Any
    description: str | None = None
    is_public: bool = True


class SiteSettingOut(SiteSettingWrite, ORMModel):
    id: str
    key: str
    updated_at: datetime


class ProfileWrite(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    role: str = Field(min_length=1, max_length=160)
    location: str | None = None
    email: EmailStr | None = None
    headline: str | None = None
    biography: str | None = None
    resume_url: str | None = None
    avatar_media_id: str | None = None
    social_links: list[dict[str, Any]] = []
    working_set: list[dict[str, Any]] = []
    currently: list[dict[str, Any]] = []
    extra: dict[str, Any] = {}


class ProfileOut(ProfileWrite, ORMModel):
    id: str
    avatar_url: str | None = None
    avatar_alt: str | None = None
    updated_at: datetime


class PageContentWrite(BaseModel):
    page: str
    section: str
    sort_order: int = 0
    enabled: bool = True
    content: dict[str, Any] = {}


class PageContentOut(PageContentWrite, ORMModel):
    id: str
    updated_at: datetime


class ProjectWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    index_label: str
    title: str
    domain: str
    status: str
    year: str | None = None
    question: str | None = None
    thesis: str | None = None
    summary: str | None = None
    featured: bool = False
    published: bool = False
    sort_order: int = 0
    cover_media_id: str | None = None
    metrics: list[dict[str, Any]] = []
    pipeline: list[dict[str, Any]] = []
    trace: dict[str, Any] = {}
    sections: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    technologies: list[str] = []
    extra: dict[str, Any] = {}


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index_label: str | None = None
    title: str | None = None
    domain: str | None = None
    status: str | None = None
    year: str | None = None
    question: str | None = None
    thesis: str | None = None
    summary: str | None = None
    featured: bool | None = None
    published: bool | None = None
    sort_order: int | None = None
    cover_media_id: str | None = None
    metrics: list[dict[str, Any]] | None = None
    pipeline: list[dict[str, Any]] | None = None
    trace: dict[str, Any] | None = None
    sections: list[dict[str, Any]] | None = None
    links: list[dict[str, Any]] | None = None
    technologies: list[str] | None = None
    extra: dict[str, Any] | None = None


class ProjectOut(ProjectWrite, ORMModel):
    id: str
    cover_url: str | None = None
    cover_alt: str | None = None
    created_at: datetime
    updated_at: datetime


class FieldNoteWrite(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str
    excerpt: str
    body: str = ""
    note_type: str = "Observation"
    tags: list[str] = []
    project_slug: str | None = None
    reading_minutes: int = Field(default=1, ge=1)
    published_at: datetime | None = None
    published: bool = False
    featured: bool = False
    cover_media_id: str | None = None
    content_blocks: list[dict[str, Any]] = []
    seo: dict[str, Any] = {}


class FieldNotePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    excerpt: str | None = None
    body: str | None = None
    note_type: str | None = None
    tags: list[str] | None = None
    project_slug: str | None = None
    reading_minutes: int | None = Field(default=None, ge=1)
    published_at: datetime | None = None
    published: bool | None = None
    featured: bool | None = None
    cover_media_id: str | None = None
    content_blocks: list[dict[str, Any]] | None = None
    seo: dict[str, Any] | None = None


class FieldNoteOut(FieldNoteWrite, ORMModel):
    id: str
    cover_url: str | None = None
    cover_alt: str | None = None
    created_at: datetime
    updated_at: datetime


class MediaOut(ORMModel):
    id: str
    filename: str
    public_url: str
    mime_type: str
    size_bytes: int
    alt_text: str | None
    caption: str | None
    kind: str
    purpose: str = "general"
    related_project: str | None = None
    created_at: datetime


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    topic: str = Field(min_length=2, max_length=160)
    message: str = Field(min_length=10, max_length=5000)
    website: str = ""


class ContactOut(ORMModel):
    id: str
    name: str
    email: EmailStr
    topic: str
    message: str
    status: str
    source: str
    created_at: datetime


class ContactStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(new|read|replied|archived|spam)$")


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[dict[str, str]] = []


class RAGSource(BaseModel):
    title: str
    url: str
    source_type: str
    excerpt: str
    score: float


class SuggestedAction(BaseModel):
    label: str
    url: str


class AIChatResponse(BaseModel):
    answer: str
    sources: list[RAGSource] = []
    suggested_actions: list[SuggestedAction] = []


class ReindexRequest(BaseModel):
    source_types: list[str] | None = None
    force: bool = False


class ReindexResponse(BaseModel):
    documents_seen: int
    documents_updated: int
    documents_unchanged: int
    chunks_embedded: int
    documents_removed: int


class KnowledgeStatus(BaseModel):
    documents: int
    chunks: int
    embedded_chunks: int
    source_counts: dict[str, int]
    embedding_model: str


class AssistantMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(max_length=6000)


class ContentAssistantRequest(BaseModel):
    message: str = Field(min_length=2, max_length=6000)
    history: list[AssistantMessage] = []


class ContentProposal(BaseModel):
    action: str = Field(pattern=r"^(create_field_note|update_field_note|create_project|update_project|update_profile|upsert_setting|create_page_section)$")
    summary: str
    payload: dict[str, Any]
    warnings: list[str] = []


class ContentAssistantResponse(BaseModel):
    message: str
    proposal: ContentProposal | None = None


class ExecuteProposalRequest(BaseModel):
    proposal: ContentProposal


class ExecuteProposalResponse(BaseModel):
    action: str
    record_id: str
    message: str


class KnowledgeDocumentOut(ORMModel):
    id: str
    source_type: str
    source_id: str
    title: str
    url: str
    content_hash: str
    enabled: bool
    metadata_json: dict[str, Any]
    updated_at: datetime


class KnowledgeUploadPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=2000)
    visibility: str | None = Field(default=None, pattern=r"^(public|internal|private)$")
    related_project: str | None = Field(default=None, max_length=160)
    citation_label: str | None = Field(default=None, max_length=240)
    enabled: bool | None = None


class KnowledgeUploadOut(ORMModel):
    id: str
    title: str
    description: str | None
    filename: str
    storage_key: str
    public_url: str
    mime_type: str
    size_bytes: int
    document_type: str
    visibility: str
    related_project: str | None
    citation_label: str | None
    status: str
    error: str | None
    enabled: bool
    content_hash: str
    chunk_count: int
    indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime
