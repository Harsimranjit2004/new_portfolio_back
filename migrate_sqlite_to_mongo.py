"""One-time data migration: copy existing SQLite content into MongoDB.

Run once, before the app starts using Mongo. Safe to re-run only against an
empty database (it does not upsert / dedupe).
"""

import json
import sqlite3
from datetime import datetime, timezone

from app.database import ensure_indexes, get_db
from app.models import FIELD_NOTES, PAGE_CONTENTS, PROFILES, PROJECTS, SITE_SETTINGS


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def row_dict(row: sqlite3.Row, json_fields: set[str], bool_fields: set[str]) -> dict:
    data = {}
    for key in row.keys():
        if key == "id":
            continue
        value = row[key]
        if key in json_fields and value is not None:
            value = json.loads(value)
        elif key in bool_fields and value is not None:
            value = bool(value)
        elif key in ("created_at", "updated_at", "published_at"):
            value = parse_dt(value)
        data[key] = value
    return data


def main() -> None:
    con = sqlite3.connect("portfolio.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    db = get_db()
    ensure_indexes(db)

    cur.execute("SELECT * FROM profiles LIMIT 1")
    row = cur.fetchone()
    if row and db[PROFILES].count_documents({}) == 0:
        doc = row_dict(row, {"social_links", "working_set", "currently", "extra"}, set())
        db[PROFILES].insert_one(doc)
        print("migrated profile")

    cur.execute("SELECT * FROM site_settings")
    rows = cur.fetchall()
    if rows and db[SITE_SETTINGS].count_documents({}) == 0:
        docs = [row_dict(r, {"value"}, {"is_public"}) for r in rows]
        db[SITE_SETTINGS].insert_many(docs)
        print(f"migrated {len(docs)} site settings")

    cur.execute("SELECT * FROM page_contents")
    rows = cur.fetchall()
    if rows and db[PAGE_CONTENTS].count_documents({}) == 0:
        docs = [row_dict(r, {"content"}, {"enabled"}) for r in rows]
        db[PAGE_CONTENTS].insert_many(docs)
        print(f"migrated {len(docs)} page content sections")

    cur.execute("SELECT * FROM projects")
    rows = cur.fetchall()
    if rows and db[PROJECTS].count_documents({}) == 0:
        json_fields = {"metrics", "pipeline", "trace", "sections", "links", "technologies", "extra"}
        docs = [row_dict(r, json_fields, {"featured", "published"}) for r in rows]
        db[PROJECTS].insert_many(docs)
        print(f"migrated {len(docs)} projects")

    cur.execute("SELECT * FROM field_notes")
    rows = cur.fetchall()
    if rows and db[FIELD_NOTES].count_documents({}) == 0:
        json_fields = {"tags", "content_blocks", "seo"}
        docs = [row_dict(r, json_fields, {"featured", "published"}) for r in rows]
        db[FIELD_NOTES].insert_many(docs)
        print(f"migrated {len(docs)} field notes")

    con.close()
    print("done")


if __name__ == "__main__":
    main()
