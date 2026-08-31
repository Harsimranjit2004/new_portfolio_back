from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database

from ..models import MEDIA_ASSETS, doc_out


def resolve_media(db: Database, media_id: str | None) -> dict | None:
    if not media_id:
        return None
    try:
        asset = db[MEDIA_ASSETS].find_one({"_id": ObjectId(media_id)})
    except (InvalidId, TypeError):
        return None
    return doc_out(asset) if asset else None


def with_avatar(db: Database, profile: dict) -> dict:
    result = doc_out(profile)
    asset = resolve_media(db, profile.get("avatar_media_id"))
    result["avatar_url"] = asset.get("public_url") if asset else None
    result["avatar_alt"] = asset.get("alt_text") if asset else None
    return result


def with_cover(db: Database, record: dict) -> dict:
    result = doc_out(record)
    asset = resolve_media(db, record.get("cover_media_id"))
    result["cover_url"] = asset.get("public_url") if asset else None
    result["cover_alt"] = asset.get("alt_text") if asset else None
    return result
