import secrets

from fastapi import Header, HTTPException, status

from .config import get_settings
from .services.auth_service import verify_session_token


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")
    if secrets.compare_digest(x_admin_key, settings.admin_api_key):
        return
    if verify_session_token(x_admin_key, settings.admin_api_key):
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin API key")
