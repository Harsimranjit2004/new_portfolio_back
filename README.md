# Portfolio Backend

A separate FastAPI service for dynamic portfolio content, media, contact messages, and the future AI assistant.

## Architecture

```text
app/
  main.py                 FastAPI composition and startup
  config.py               Environment configuration
  database.py             PyMongo client/database + index setup
  models.py               Mongo collection names + doc helpers
  schemas.py              Request/response contracts
  dependencies.py         Admin API-key guard
  routers/
    health.py
    profile.py
    site.py
    projects.py
    field_notes.py
    media.py
    contact.py
    ai.py
  services/
    seed_service.py
    media_service.py
    email_service.py
    ai_service.py
storage/                   Local development uploads
```

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`

## Admin authorization

Public GET endpoints require no secret. All content mutations and inbox/media administration require:

```http
X-Admin-Key: the-value-from-ADMIN_API_KEY
```

That raw key still works directly (scripts, curl), but the admin UI logs in with a username and
password instead of pasting the key. Set `ADMIN_USERNAME` and generate `ADMIN_PASSWORD_HASH` with:

```bash
python -m app.scripts.hash_password
```

`POST /api/v1/auth/login` (`{ "username", "password" }`) verifies the credentials and returns a
signed, time-limited session token (12h). Send that token as `X-Admin-Key` exactly like the raw
key — `require_admin` accepts either.

Never put `ADMIN_API_KEY`, `ADMIN_PASSWORD_HASH`, SMTP credentials, or `OPENAI_API_KEY` in the frontend.

## Route map

### Profile

- `GET /api/v1/profile`
- `PUT /api/v1/profile` (admin)

Controls name, role, location, email, headline, biography, résumé URL, avatar, social links, working set, current activity, and arbitrary extra profile data.

### Site and page content

- `GET /api/v1/site/settings`
- `PUT /api/v1/site/settings/{key}` (admin)
- `DELETE /api/v1/site/settings/{key}` (admin)
- `GET /api/v1/site/pages/{page}`
- `GET /api/v1/site/pages/{page}/admin` (admin)
- `POST /api/v1/site/pages` (admin)
- `PUT /api/v1/site/pages/{section_id}` (admin)
- `DELETE /api/v1/site/pages/{section_id}` (admin)

Use page sections for small editable details: hero copy, navigation labels, footer readouts, About sections, Contact copy, orb labels, and any future UI content.

### Projects

- `GET /api/v1/projects`
- `GET /api/v1/projects/{slug}`
- `GET /api/v1/projects/admin` (admin)
- `POST /api/v1/projects` (admin)
- `PATCH /api/v1/projects/{slug}` (admin)
- `DELETE /api/v1/projects/{slug}` (admin)

Project records support metrics, pipelines, trace rows, arbitrary case-study sections, links, technologies, cover media, status, ordering, featured state, and publishing state.

### Field Notes

- `GET /api/v1/field-notes`
- `GET /api/v1/field-notes/{slug}`
- `GET /api/v1/field-notes/admin` (admin)
- `POST /api/v1/field-notes` (admin)
- `PATCH /api/v1/field-notes/{slug}` (admin)
- `DELETE /api/v1/field-notes/{slug}` (admin)

Filters include `tag`, `project`, `search`, and `limit`. Notes support Markdown/body text, structured content blocks, tags, note types, cover media, SEO, featured state, drafts, and publishing dates.

### Media

- `GET /api/v1/media-assets` (admin)
- `POST /api/v1/media-assets` multipart upload (admin)
- `PATCH /api/v1/media-assets/{id}` (admin)
- `DELETE /api/v1/media-assets/{id}` (admin)
- Public files: `GET /media/{storage_key}`

Local disk storage is suitable for development. Replace `media_service.py` with S3, Cloudinary, or Vercel Blob before serverless production deployment.

### Contact

- `POST /api/v1/contact`
- `GET /api/v1/contact` (admin)
- `PATCH /api/v1/contact/{id}` (admin)
- `DELETE /api/v1/contact/{id}` (admin)

Messages are always stored. If SMTP is configured, email delivery runs as a background task. Python uses `smtplib`; Nodemailer is Node.js-only.

### AI and RAG

- `POST /api/v1/ai/chat` — evidence-grounded portfolio answers with citations
- `POST /api/v1/ai/reindex` (admin) — incremental or forced index rebuild
- `GET /api/v1/ai/status` (admin) — document/chunk/source counts
- `GET /api/v1/ai/sources` (admin) — inspect indexed sources
- `PATCH /api/v1/ai/sources/{id}/toggle` (admin) — enable/disable a source
- `DELETE /api/v1/ai/index` (admin) — clear the index

The ingestion pipeline reads published projects and Field Notes plus profile, page sections, and public site settings. Documents are content-hashed, overlap-chunked, embedded in batches, and updated incrementally. Content mutations automatically schedule a refresh for their source family when OpenAI is configured.

Manual CLI pipeline:

```bash
python -m app.scripts.reindex
python -m app.scripts.reindex --source project --source field_note
python -m app.scripts.reindex --force
```

The first complete build requires `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_EMBEDDING_MODEL`. The provider must expose OpenAI-compatible `/embeddings` and `/chat/completions` endpoints.

Retrieval uses cosine similarity computed in Python over documents stored in the `knowledge_chunks` collection. This is appropriate for the current small portfolio corpus. For a much larger corpus, move to MongoDB Atlas Vector Search (`$vectorSearch` aggregation stage over an Atlas Search index) instead of brute-force scoring.

## Database

MongoDB (Atlas or self-hosted). Set:

```env
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/portfolio?appName=Cluster0
```

Collections are schemaless; `database.py`'s `ensure_indexes()` creates the unique indexes the app relies on (settings key, project/field-note slugs, media storage key, knowledge document source identity) on startup.

## Production notes

- Use PostgreSQL.
- Use S3/Cloudinary/Vercel Blob instead of local uploads.
- Set explicit CORS origins.
- Rotate `ADMIN_API_KEY`.
- Add request rate limiting to Contact and AI routes.
- Add Alembic migrations.
- Run the RAG reindex after initial content import.
- For larger corpora, migrate JSON embeddings to pgvector/Qdrant.
- Deploy on Render, Railway, Fly.io, or another persistent Python host. Vercel serverless requires different handling for uploads and database connections.

## Import current frontend defaults

The idempotent migration imports the current profile, global settings, page sections, seven projects, and seven Field Notes.

Run safely and create missing records only:

    python -m app.scripts.import_frontend_defaults

Overwrite matching seeded records with the values in the script:

    python -m app.scripts.import_frontend_defaults --update-existing

Import and immediately build the RAG index after OpenAI is configured:

    python -m app.scripts.import_frontend_defaults --reindex

Make shortcuts:

    make seed
    make seed-update
    make seed-reindex

## Cloudflare R2 setup

Production uploads support Cloudflare R2 while local development continues to use `storage/`.

1. Create an R2 bucket in Cloudflare.
2. Create an R2 API token with Object Read & Write access limited to that bucket.
3. Enable a public development URL or attach a custom public domain to the bucket.
4. Configure production environment variables:

```env
STORAGE_PROVIDER=r2
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=portfolio-media
R2_PUBLIC_BASE_URL=https://media.example.com
MAX_UPLOAD_MB=10
```

`R2_PUBLIC_BASE_URL` must not end with a slash. Keep all R2 credentials in the backend host only. For local development, use `STORAGE_PROVIDER=local`.

## Gmail SMTP setup

Use a Google App Password; never use your normal Gmail password.

1. Enable two-step verification on the sending Google account.
2. Open Google Account → Security → App passwords.
3. Create an app password named `Portfolio Backend`.
4. Configure:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-address@gmail.com
SMTP_PASSWORD=the-16-character-app-password
SMTP_FROM=your-address@gmail.com
CONTACT_TO=the-address-that-should-receive-messages@gmail.com
SMTP_USE_TLS=true
```

After configuring the backend environment, run:

```bash
python -m app.scripts.test_email
```

Contact submissions are saved to MongoDB even if SMTP delivery fails. Delivery failures are written to backend logs without exposing SMTP credentials to the client.

## Dynamic RAG knowledge library

Published projects, Field Notes, profile data, public page sections, and public settings are content-hashed and incrementally indexed. Content mutations queue a refresh for only the affected source family. A deterministic graph is rebuilt from project technologies/domains, Field Note relationships, and public uploaded-document relationships.

Admin knowledge-document routes:

- `GET /api/v1/knowledge-documents`
- `POST /api/v1/knowledge-documents` — multipart PDF, DOCX, Markdown, or text upload
- `PATCH /api/v1/knowledge-documents/{id}` — metadata, visibility, and enabled state
- `POST /api/v1/knowledge-documents/{id}/reindex`
- `DELETE /api/v1/knowledge-documents/{id}`

Only uploads with `visibility=public` and `enabled=true` enter the public assistant index. Uploaded originals are stored by the configured media storage provider. Chat responses include up to three deterministic sources and two suggested actions whose URLs come from indexed metadata, never from model-generated links.
