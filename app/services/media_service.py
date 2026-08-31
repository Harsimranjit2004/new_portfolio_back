import re
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from ..config import Settings, get_settings

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml",
    "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "text/markdown", "text/x-markdown", "video/mp4", "video/webm",
}


def safe_name(filename: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", Path(filename).name).strip("-")
    return stem or "asset"


def _object_key(filename: str) -> str:
    return f"uploads/{uuid4().hex}-{safe_name(filename)}"


def _public_url(settings: Settings, key: str) -> str:
    if settings.storage_provider == "r2":
        return f"{settings.r2_public_base_url.rstrip('/')}/{key}"
    return f"{settings.public_base_url.rstrip('/')}/media/{key}"


@lru_cache
def _r2_client():
    settings = get_settings()
    missing = [
        name for name, value in {
            "R2_ACCOUNT_ID": settings.r2_account_id,
            "R2_ACCESS_KEY_ID": settings.r2_access_key_id,
            "R2_SECRET_ACCESS_KEY": settings.r2_secret_access_key,
            "R2_BUCKET_NAME": settings.r2_bucket_name,
            "R2_PUBLIC_BASE_URL": settings.r2_public_base_url,
        }.items() if not value
    ]
    if missing:
        raise RuntimeError(f"Missing R2 configuration: {', '.join(missing)}")

    import boto3

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


async def save_upload(file: UploadFile) -> tuple[str, str, int]:
    settings = get_settings()
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported media type")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large")

    key = _object_key(file.filename or "asset")
    if settings.storage_provider == "r2":
        try:
            _r2_client().put_object(
                Bucket=settings.r2_bucket_name,
                Key=key,
                Body=content,
                ContentType=file.content_type or "application/octet-stream",
                CacheControl="public, max-age=31536000, immutable",
            )
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Object storage upload failed") from exc
    elif settings.storage_provider == "local":
        path = settings.upload_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    else:
        raise RuntimeError(f"Unsupported storage provider: {settings.storage_provider}")

    return key, _public_url(settings, key), len(content)


def delete_upload(storage_key: str) -> None:
    settings = get_settings()
    if settings.storage_provider == "r2":
        _r2_client().delete_object(Bucket=settings.r2_bucket_name, Key=storage_key)
        return
    if settings.storage_provider != "local":
        raise RuntimeError(f"Unsupported storage provider: {settings.storage_provider}")

    path = settings.upload_path / storage_key
    if path.exists() and path.is_file():
        path.unlink()
