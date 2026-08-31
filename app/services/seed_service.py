from pymongo.database import Database

from ..models import PAGE_CONTENTS, PROFILES, SITE_SETTINGS, utcnow


def _book_cover(isbn: str) -> str:
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"


def seed_defaults(db: Database) -> None:
    now = utcnow()
    if db[PROFILES].count_documents({}) == 0:
        db[PROFILES].insert_one({
            "name": "Harsimranjit",
            "role": "ML / AI Engineer",
            "location": "Toronto, Canada",
            "email": None,
            "headline": "I build ML systems and the infrastructure around them.",
            "biography": (
                "I spend much of my time building and studying machine-learning systems, but the same "
                "curiosity that pulls me into models and infrastructure also pulls me toward books, nature, "
                "photography, golf, and exploring things outside technology."
            ),
            "resume_url": None,
            "avatar_media_id": None,
            "social_links": [
                {"label": "GitHub", "url": "https://github.com/"},
                {"label": "LinkedIn", "url": "https://www.linkedin.com/"},
            ],
            "working_set": [{"name": name} for name in [
                "Machine Learning Systems", "Model Infrastructure", "Recommendation Systems",
                "Backend Systems", "Cloud Infrastructure", "Evaluation & Experimentation", "System Design",
            ]],
            "currently": [{"name": name} for name in [
                "Python", "C++", "TypeScript", "JavaScript", "PyTorch", "FastAPI", "React", "Next.js",
                "Node.js", "PostgreSQL", "MongoDB", "AWS", "Docker", "Kubernetes", "Git",
            ]],
            "extra": {
                "experience": [
                    {"period": "2025 — PRESENT", "role": "ML Engineer", "company": "Stikbook", "description": "ML/AI systems, recommendation systems, backend infrastructure, and production workflows.", "placeholder": False},
                    {"period": "2024 — 2025", "role": "Previous role — details pending", "company": "Company information to add", "description": "Add verified responsibilities and outcomes for this experience.", "placeholder": True},
                    {"period": "EARLIER", "role": "Previous role — details pending", "company": "Company information to add", "description": "Add verified professional information for this timeline entry.", "placeholder": True},
                ],
                "books": [
                    {"title": "L’Étranger", "author": "Albert Camus", "cover": _book_cover("9782070360024"), "shelf": "current", "status": "reading", "note": "Part novel. Part French lesson.", "category": "Literary fiction", "height": 214, "color": "#eee9df"},
                    {"title": "Atomic Habits", "author": "James Clear", "cover": _book_cover("9780735211292"), "shelf": "current", "category": "Habits · Psychology", "height": 202, "color": "#f2eee5"},
                    {"title": "The Almanack of Naval Ravikant", "author": "Eric Jorgenson", "cover": _book_cover("9781544514215"), "shelf": "current", "category": "Ideas · Life", "height": 190, "color": "#eee9df"},
                    {"title": "The Design of Everyday Things", "author": "Don Norman", "cover": _book_cover("9780465050659"), "shelf": "current", "category": "Design", "height": 204, "color": "#e4b231"},
                    {"title": "Poor Charlie’s Almanack", "author": "Charles T. Munger", "cover": _book_cover("9781578645015"), "shelf": "current", "category": "Mental models", "height": 210, "color": "#183249", "ink": "#f5e5bb"},
                    {"title": "The Pragmatic Programmer", "author": "David Thomas & Andrew Hunt", "cover": _book_cover("9780135957059"), "shelf": "current", "category": "Software engineering", "height": 198, "color": "#202321", "ink": "#f3f0df"},
                    {"title": "Sapiens", "author": "Yuval Noah Harari", "cover": _book_cover("9780062316097"), "shelf": "current", "category": "History · Ideas", "height": 207, "color": "#eee6d9"},
                    {"title": "Deep Work", "author": "Cal Newport", "cover": _book_cover("9781455586691"), "shelf": "read", "category": "Focus", "height": 194, "color": "#e9c33d"},
                    {"title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "cover": _book_cover("9781449373320"), "shelf": "read", "category": "Systems", "height": 211, "color": "#eee7dc"},
                    {"title": "Clean Code", "author": "Robert C. Martin", "cover": _book_cover("9780132350884"), "shelf": "read", "category": "Software engineering", "height": 188, "color": "#161b20", "ink": "#fff"},
                    {"title": "The Psychology of Money", "author": "Morgan Housel", "cover": _book_cover("9780857197689"), "shelf": "read", "category": "Psychology · Money", "height": 205, "color": "#f0ede5"},
                    {"title": "Range", "author": "David Epstein", "cover": _book_cover("9780735214484"), "shelf": "read", "category": "Learning · Generalists", "height": 198, "color": "#9ecfc4"},
                    {"title": "The Obstacle Is the Way", "author": "Ryan Holiday", "cover": _book_cover("9781591846352"), "shelf": "read", "category": "Stoicism", "height": 208, "color": "#eee8dc"},
                    {"title": "Hooked", "author": "Nir Eyal", "cover": _book_cover("9781591847786"), "shelf": "read", "category": "Product · Psychology", "height": 180, "color": "#e5bc2c"},
                    {"title": "Zero to One", "author": "Peter Thiel", "cover": _book_cover("9780804139298"), "shelf": "return", "category": "Startups · Ideas", "height": 206, "color": "#a9c7df"},
                    {"title": "Made to Stick", "author": "Chip Heath & Dan Heath", "cover": _book_cover("9781400064281"), "shelf": "return", "category": "Communication", "height": 188, "color": "#df6031", "ink": "#fff"},
                    {"title": "The Lean Startup", "author": "Eric Ries", "cover": _book_cover("9780307887894"), "shelf": "return", "category": "Startups", "height": 201, "color": "#2876a8", "ink": "#fff"},
                    {"title": "Creativity, Inc.", "author": "Ed Catmull", "cover": _book_cover("9780812993011"), "shelf": "return", "category": "Creativity · Teams", "height": 214, "color": "#9c292b", "ink": "#fff"},
                    {"title": "Thinking, Fast and Slow", "author": "Daniel Kahneman", "cover": _book_cover("9780374533557"), "shelf": "return", "category": "Psychology · Decisions", "height": 196, "color": "#f2efe8"},
                ],
            },
            "created_at": now, "updated_at": now,
        })
    if db[SITE_SETTINGS].count_documents({}) == 0:
        db[SITE_SETTINGS].insert_many([
            {"key": "site.navigation", "value": ["Work", "Field Notes", "About", "Contact"], "description": "Main navigation labels", "is_public": True, "created_at": now, "updated_at": now},
            {"key": "site.footer", "value": {"location": "Toronto", "year": 2026, "channel_open": True}, "description": None, "is_public": True, "created_at": now, "updated_at": now},
            {"key": "home.hero", "value": {"eyebrow": "Engineering beneath the surface", "disciplines": ["Machine learning", "ML systems", "Research & experimentation"]}, "description": None, "is_public": True, "created_at": now, "updated_at": now},
        ])
    if db[PAGE_CONTENTS].count_documents({}) == 0:
        db[PAGE_CONTENTS].insert_one({
            "page": "home", "section": "descent_statement", "sort_order": 0, "enabled": True,
            "content": {"lines": ["The result is only the surface.", "The interesting part is", "what made it possible."]},
            "created_at": now, "updated_at": now,
        })
